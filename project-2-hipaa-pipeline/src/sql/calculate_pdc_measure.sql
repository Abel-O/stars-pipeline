-- Project 1: Medicare Stars Measure Analytics Platform
-- Script: calculate_pdc_measure.sql
-- Description: Calculates Proportion of Days Covered (PDC) for Medication Adherence (Diabetes)
-- Methodology: CMS Part D Star Ratings Technical Notes

-- Step 1: Identify Target Population (Denominator)
-- Members with at least 2 fills for Diabetes meds on different dates of service
CREATE OR REPLACE TABLE `project_1_stars.pdc_diabetes_denominator` AS
WITH diabetes_fills AS (
    SELECT 
        member_id,
        fill_date,
        drug_name,
        days_supply
    FROM `project_1_stars.pharmacy_claims`
    WHERE drug_category = 'Diabetes'
    AND fill_date BETWEEN '2023-01-01' AND '2023-12-31'
),
fill_counts AS (
    SELECT 
        member_id,
        COUNT(DISTINCT fill_date) as unique_fill_dates
    FROM diabetes_fills
    GROUP BY member_id
    HAVING unique_fill_dates >= 2
)
SELECT 
    m.member_id,
    m.plan_id,
    m.enrollment_start_date,
    m.enrollment_end_date
FROM `project_1_stars.members` m
JOIN fill_counts fc ON m.member_id = fc.member_id
WHERE m.status = 'Active';

-- Step 2: Calculate Covered Days (Numerator)
-- Logic: Array-based day coverage calculation to handle overlapping fills
CREATE OR REPLACE TABLE `project_1_stars.pdc_diabetes_numerator` AS
WITH date_range AS (
    SELECT date FROM UNNEST(GENERATE_DATE_ARRAY('2023-01-01', '2023-12-31')) as date
),
member_fills AS (
    SELECT 
        d.member_id,
        pc.fill_date,
        pc.days_supply,
        DATE_ADD(pc.fill_date, INTERVAL pc.days_supply - 1 DAY) as end_date
    FROM `project_1_stars.pdc_diabetes_denominator` d
    JOIN `project_1_stars.pharmacy_claims` pc ON d.member_id = pc.member_id
    WHERE pc.drug_category = 'Diabetes'
),
daily_coverage AS (
    SELECT 
        mf.member_id,
        dr.date,
        MAX(CASE WHEN dr.date BETWEEN mf.fill_date AND mf.end_date THEN 1 ELSE 0 END) as is_covered
    FROM member_fills mf
    CROSS JOIN date_range dr
    GROUP BY mf.member_id, dr.date
)
SELECT 
    member_id,
    SUM(is_covered) as covered_days
FROM daily_coverage
GROUP BY member_id;

-- Step 3: Calculate Final PDC Score
-- Threshold: PDC >= 80% is considered "Adherent"
CREATE OR REPLACE TABLE `project_1_stars.pdc_diabetes_scores` AS
SELECT 
    d.member_id,
    d.plan_id,
    COALESCE(n.covered_days, 0) as covered_days,
    DATE_DIFF(d.enrollment_end_date, d.enrollment_start_date, DAY) + 1 as denominator_days,
    SAFE_DIVIDE(COALESCE(n.covered_days, 0), (DATE_DIFF(d.enrollment_end_date, d.enrollment_start_date, DAY) + 1)) as pdc_score,
    CASE 
        WHEN SAFE_DIVIDE(COALESCE(n.covered_days, 0), (DATE_DIFF(d.enrollment_end_date, d.enrollment_start_date, DAY) + 1)) >= 0.80 THEN 1 
        ELSE 0 
    END as is_adherent
FROM `project_1_stars.pdc_diabetes_denominator` d
LEFT JOIN `project_1_stars.pdc_diabetes_numerator` n ON d.member_id = n.member_id;

-- Step 4: Plan Level Summary
SELECT 
    plan_id,
    COUNT(member_id) as eligible_members,
    SUM(is_adherent) as adherent_members,
    ROUND(SUM(is_adherent) / COUNT(member_id) * 100, 2) as star_rating_score
FROM `project_1_stars.pdc_diabetes_scores`
GROUP BY plan_id;
