import pandas as pd
import numpy as np
from faker import Faker
import random
from datetime import datetime, timedelta
import os

# Initialize Faker
fake = Faker()
Faker.seed(42)
np.random.seed(42)

# Configuration
NUM_MEMBERS = 1000
NUM_PROVIDERS = 50
NUM_PLANS = 5
START_DATE = datetime(2023, 1, 1)
END_DATE = datetime(2023, 12, 31)
OUTPUT_DIR = 'data'

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def generate_plans():
    print("Generating Plans...")
    plans = []
    for i in range(NUM_PLANS):
        plans.append({
            'plan_id': f'H{1000+i}',
            'plan_name': f'CVS Health Star Plan {i+1}',
            'contract_number': f'H{1000+i}',
            'plan_type': np.random.choice(['HMO', 'PPO'], p=[0.7, 0.3])
        })
    return pd.DataFrame(plans)

def generate_providers():
    print("Generating Providers...")
    providers = []
    specialties = ['Family Practice', 'Internal Medicine', 'Cardiology', 'Endocrinology', 'General Practice']
    for i in range(NUM_PROVIDERS):
        providers.append({
            'provider_id': f'PR{10000+i}',
            'npi': fake.unique.random_number(digits=10),
            'first_name': fake.first_name(),
            'last_name': fake.last_name(),
            'specialty': np.random.choice(specialties),
            'network_status': 'In-Network'
        })
    return pd.DataFrame(providers)

def generate_members(plans_df):
    print("Generating Members...")
    members = []
    plan_ids = plans_df['plan_id'].tolist()
    
    for i in range(NUM_MEMBERS):
        dob = fake.date_of_birth(minimum_age=65, maximum_age=90)
        members.append({
            'member_id': f'MEM{100000+i}',
            'first_name': fake.first_name(),
            'last_name': fake.last_name(),
            'dob': dob,
            'gender': np.random.choice(['M', 'F']),
            'plan_id': np.random.choice(plan_ids),
            'enrollment_start_date': START_DATE,
            'enrollment_end_date': END_DATE,
            'status': 'Active'
        })
    return pd.DataFrame(members)

def generate_pharmacy_claims(members_df):
    print("Generating Pharmacy Claims (Part D)...")
    claims = []
    member_ids = members_df['member_id'].tolist()
    
    # Medications for PDC measures (Diabetes, Hypertension, Cholesterol)
    medications = {
        'Diabetes': ['Metformin', 'Insulin', 'Glipizide'],
        'RASA': ['Lisinopril', 'Losartan', 'Valsartan'], # Hypertension
        'Statins': ['Atorvastatin', 'Simvastatin', 'Rosuvastatin']
    }
    
    for _ in range(NUM_MEMBERS * 12): # Avg 1 script per month per member
        member_id = np.random.choice(member_ids)
        category = np.random.choice(list(medications.keys()))
        drug_name = np.random.choice(medications[category])
        
        fill_date = fake.date_between(start_date=START_DATE, end_date=END_DATE)
        days_supply = np.random.choice([30, 90], p=[0.8, 0.2])
        
        claims.append({
            'claim_id': fake.unique.uuid4(),
            'member_id': member_id,
            'fill_date': fill_date,
            'drug_name': drug_name,
            'drug_category': category,
            'ndc': fake.ean13(),
            'days_supply': days_supply,
            'quantity': days_supply, # Simplified
            'cost': round(np.random.uniform(10, 500), 2)
        })
    return pd.DataFrame(claims)

def generate_medical_claims(members_df, providers_df):
    print("Generating Medical Claims (Part C)...")
    claims = []
    member_ids = members_df['member_id'].tolist()
    provider_ids = providers_df['provider_id'].tolist()
    
    # Diagnosis codes for measures
    diagnoses = ['E11.9', 'I10', 'E78.5', 'Z00.00'] # Diabetes, Hypertension, Hyperlipidemia, General Exam
    
    for _ in range(NUM_MEMBERS * 5): # Avg 5 visits per year
        member_id = np.random.choice(member_ids)
        provider_id = np.random.choice(provider_ids)
        service_date = fake.date_between(start_date=START_DATE, end_date=END_DATE)
        
        claims.append({
            'claim_id': fake.unique.uuid4(),
            'member_id': member_id,
            'provider_id': provider_id,
            'service_date': service_date,
            'diagnosis_code': np.random.choice(diagnoses),
            'procedure_code': '99213', # Office visit
            'paid_amount': round(np.random.uniform(50, 200), 2)
        })
    return pd.DataFrame(claims)

def generate_cahps_surveys(members_df):
    print("Generating CAHPS Survey Data...")
    surveys = []
    # Sample 20% of members
    sampled_members = members_df.sample(frac=0.2)
    
    for _, member in sampled_members.iterrows():
        surveys.append({
            'survey_id': fake.unique.uuid4(),
            'member_id': member['member_id'],
            'survey_date': fake.date_between(start_date=datetime(2023, 3, 1), end_date=datetime(2023, 6, 30)),
            'rating_health_plan': np.random.randint(1, 11), # 0-10 scale
            'rating_drug_plan': np.random.randint(1, 11),
            'rating_health_care': np.random.randint(1, 11),
            'getting_needed_care': np.random.choice(['Never', 'Sometimes', 'Usually', 'Always'], p=[0.05, 0.1, 0.3, 0.55])
        })
    return pd.DataFrame(surveys)

if __name__ == "__main__":
    plans_df = generate_plans()
    providers_df = generate_providers()
    members_df = generate_members(plans_df)
    pharmacy_claims_df = generate_pharmacy_claims(members_df)
    medical_claims_df = generate_medical_claims(members_df, providers_df)
    cahps_df = generate_cahps_surveys(members_df)
    
    # Save to CSV
    plans_df.to_csv(f'{OUTPUT_DIR}/plans.csv', index=False)
    providers_df.to_csv(f'{OUTPUT_DIR}/providers.csv', index=False)
    members_df.to_csv(f'{OUTPUT_DIR}/members.csv', index=False)
    pharmacy_claims_df.to_csv(f'{OUTPUT_DIR}/pharmacy_claims.csv', index=False)
    medical_claims_df.to_csv(f'{OUTPUT_DIR}/medical_claims.csv', index=False)
    cahps_df.to_csv(f'{OUTPUT_DIR}/cahps_surveys.csv', index=False)
    
    print(f"Data generation complete. Files saved to {OUTPUT_DIR}/")
