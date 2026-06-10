import pandas as pd
import numpy as np
import re

def calculate_dq(df):
    total = len(df)
    # 1. Completeness (avg across NIB, NPWP, NAMA)
    comp = (1 - df[['NIB', 'NPWP', 'NAMA_PERUSAHAAN']].isna().mean().mean()) * 100
    
    # 2. Validity (NPWP format)
    NPWP_PATTERN = r'^\d{2}\.\d{3}\.\d{3}\.\d{1}-\d{3}\.\d{3}$'
    valid = df['NPWP'].apply(lambda x: bool(re.match(NPWP_PATTERN, str(x))) if pd.notna(x) else False).mean() * 100
    
    # 3. Uniqueness (NIB)
    unique = (1 - df.duplicated(subset=['NIB']).sum() / total) * 100 if total > 0 else 0
    
    return {'Completeness': comp, 'Validity': valid, 'Uniqueness': unique, 'Score': np.mean([comp, valid, unique])}

# Load
df_oss = pd.read_csv('data/raw/oss_nib_data.csv')
df_ceisa = pd.read_csv('data/raw/ceisa_data.csv')
df_golden = pd.read_csv('data/golden/golden_record_djbc.csv')

# Score
s_oss = calculate_dq(df_oss)
s_ceisa = calculate_dq(df_ceisa)
s_golden = calculate_dq(df_golden)

# Report
report = pd.DataFrame([s_oss, s_ceisa, s_golden], index=['OSS', 'CEISA', 'GOLDEN'])
print("="*45)
print(f"{'Source':<10} {'Comp.':>8} {'Valid.':>8} {'Uniq.':>8} {'Overall':>8}")
print("-"*45)
for idx, row in report.iterrows():
    print(f"{idx:<10} {row['Completeness']:>7.1f}% {row['Validity']:>7.1f}% {row['Uniqueness']:>7.1f}% {row['Score']:>7.1f}%")
print("="*45)

report.to_csv('reports/dq_scorecard_final.csv')
print("Final scorecard saved to reports/dq_scorecard_final.csv")
