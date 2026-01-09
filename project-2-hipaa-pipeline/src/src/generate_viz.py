import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Ensure output directory exists
os.makedirs('assets', exist_ok=True)

# Load generated data
try:
    claims_df = pd.read_csv('data/pharmacy_claims.csv')
    members_df = pd.read_csv('data/members.csv')
except FileNotFoundError:
    print("Data files not found. Please run generate_data.py first.")
    exit(1)

# Merge to get plan info
merged_df = claims_df.merge(members_df, on='member_id')

# Calculate adherence (simplified proxy: claim count per plan)
# In reality, PDC is complex, but for a visual preview, we'll show claim volume by drug category
plt.figure(figsize=(12, 6))
sns.set_theme(style="whitegrid")

# Count claims by drug category and plan type
viz_data = merged_df.groupby(['drug_category', 'plan_id']).size().reset_index(name='claim_count')

# Create bar chart
ax = sns.barplot(x='drug_category', y='claim_count', hue='plan_id', data=viz_data, palette='viridis')

plt.title('Pharmacy Claim Volume by Drug Category & Plan (Simulated)', fontsize=16, pad=20)
plt.xlabel('Drug Category (HEDIS Measures)', fontsize=12)
plt.ylabel('Total Claims', fontsize=12)
plt.legend(title='Plan ID')
plt.tight_layout()

# Save the plot
output_path = 'assets/dashboard_preview.png'
plt.savefig(output_path, dpi=300)
print(f"Visualization saved to {output_path}")
