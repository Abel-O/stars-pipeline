import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, StandardOptions, GoogleCloudOptions
import argparse
import logging
import json
import hashlib

# Project 2: HIPAA-Safe Stars Data Pipeline
# Description: Ingests raw member data, tokenizes PII (Member ID), and loads to BigQuery
# Key Features: PII Tokenization, Dead Letter Queue for bad data, IAM-ready structure

class TokenizeMemberId(beam.DoFn):
    """Tokenizes Member ID using SHA-256 for HIPAA compliance (De-identification)."""
    def process(self, element):
        try:
            record = json.loads(element)
            if 'member_id' in record:
                # Salt should be managed via Secret Manager in production
                salt = "prod_salt_v1" 
                raw_id = record['member_id']
                hashed_id = hashlib.sha256((raw_id + salt).encode('utf-8')).hexdigest()
                
                # Replace raw ID with token
                record['member_id_token'] = hashed_id
                record['original_member_id_masked'] = raw_id[:3] + "****" + raw_id[-2:]
                del record['member_id'] # Remove PHI
                
                yield record
            else:
                # Missing key identifier - send to DLQ
                yield beam.pvalue.TaggedOutput('bad_records', element)
        except Exception as e:
            logging.error(f"Error processing record: {e}")
            yield beam.pvalue.TaggedOutput('bad_records', element)

class ValidateSchema(beam.DoFn):
    """Validates that required fields exist."""
    def process(self, element):
        required_fields = ['member_id_token', 'plan_id', 'status']
        if all(field in element for field in required_fields):
            yield element
        else:
            yield beam.pvalue.TaggedOutput('bad_records', json.dumps(element))

def run(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_topic', required=True, help='Pub/Sub topic to read from')
    parser.add_argument('--output_table', required=True, help='BigQuery table to write to')
    parser.add_argument('--dlq_table', required=True, help='BigQuery table for dead letter queue')
    
    known_args, pipeline_args = parser.parse_known_args(argv)
    
    options = PipelineOptions(pipeline_args)
    options.view_as(StandardOptions).streaming = True
    google_cloud_options = options.view_as(GoogleCloudOptions)
    
    # Define BigQuery Schemas
    table_schema = 'member_id_token:STRING, original_member_id_masked:STRING, plan_id:STRING, status:STRING, ingestion_ts:TIMESTAMP'
    dlq_schema = 'raw_record:STRING, error_ts:TIMESTAMP'

    with beam.Pipeline(options=options) as p:
        # Read from Pub/Sub
        messages = (p 
                    | 'ReadFromPubSub' >> beam.io.ReadFromPubSub(topic=known_args.input_topic)
                    | 'DecodeUTF8' >> beam.Map(lambda x: x.decode('utf-8')))
        
        # Process: Tokenize -> Validate
        processed_data, bad_records = (messages 
                                       | 'TokenizePII' >> beam.ParDo(TokenizeMemberId()).with_outputs('bad_records', main='main'))
        
        valid_data, invalid_schema = (processed_data 
                                      | 'ValidateSchema' >> beam.ParDo(ValidateSchema()).with_outputs('bad_records', main='main'))
        
        # Add Timestamp
        final_data = (valid_data 
                      | 'AddTimestamp' >> beam.Map(lambda x: {**x, 'ingestion_ts': datetime.now().isoformat()}))

        # Write to BigQuery (Silver Layer)
        (final_data 
         | 'WriteToBigQuery' >> beam.io.WriteToBigQuery(
             known_args.output_table,
             schema=table_schema,
             create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED,
             write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND))
        
        # Handle Bad Records (DLQ)
        all_bad_records = (bad_records, invalid_schema) | 'FlattenErrors' >> beam.Flatten()
        
        (all_bad_records 
         | 'FormatDLQ' >> beam.Map(lambda x: {'raw_record': str(x), 'error_ts': datetime.now().isoformat()})
         | 'WriteToDLQ' >> beam.io.WriteToBigQuery(
             known_args.dlq_table,
             schema=dlq_schema,
             create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED,
             write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND))

if __name__ == '__main__':
    from datetime import datetime
    logging.getLogger().setLevel(logging.INFO)
    run()
