import pandas as pd
import numpy as np
import re
from unidecode import unidecode
from datetime import datetime

class AuditTrail:
    def __init__(self, dataset_name, total_records):
        self.dataset_name = dataset_name
        self.total_records = total_records
        self.entries = []
    
    def log(self, operation, field, n_affected, description):
        entry = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'operation': operation,
            'field': field,
            'n_affected': n_affected,
            'pct_affected': round(n_affected / self.total_records * 100, 2),
            'description': description
        }
        self.entries.append(entry)
        print(f"[{self.dataset_name}] {operation} on {field}: {n_affected} records ({entry['pct_affected']}%)")

def standardize_name(name):
    if pd.isna(name): return None
    s = unidecode(str(name)).upper().strip()
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r"[^A-Z0-9\s.,\-']", '', s)
    # Standardize PT, CV, etc
    s = re.sub(r'\bPT\.*\s+', 'PT ', s)
    s = re.sub(r'\bCV\.*\s+', 'CV ', s)
    s = re.sub(r'\bPT\.*\b', 'PT', s)
    s = re.sub(r'\bCV\.*\b', 'CV', s)
    return s.strip()

def standardize_npwp(npwp):
    if pd.isna(npwp): return None
    digits = re.sub(r'\D', '', str(npwp))
    if len(digits) == 15:
        return f"{digits[0:2]}.{digits[2:5]}.{digits[5:8]}.{digits[8]}-{digits[9:12]}.{digits[12:15]}"
    return digits

def process_file(file_path, output_path, name_col, npwp_col):
    df = pd.read_csv(file_path)
    audit = AuditTrail(os.path.basename(file_path), len(df))
    
    # Clean Name
    df[name_col + '_CLEAN'] = df[name_col].apply(standardize_name)
    n_name = (df[name_col + '_CLEAN'] != df[name_col]).sum()
    audit.log('CLEAN_NAME', name_col, n_name, 'Normalized casing and legal prefixes')
    
    # Clean NPWP
    df[npwp_col + '_CLEAN'] = df[npwp_col].apply(standardize_npwp)
    n_npwp = (df[npwp_col + '_CLEAN'] != df[npwp_col]).sum()
    audit.log('CLEAN_NPWP', npwp_col, n_npwp, 'Standardized format XX.XXX.XXX.X-XXX.XXX')
    
    # Standardize Address (Simple title case)
    df['ALAMAT_CLEAN'] = df['ALAMAT'].str.title().str.strip()
    
    df.to_csv(output_path, index=False)
    return audit.entries

import os
# Process both
entries_oss = process_file('data/raw/oss_nib_data.csv', 'data/processed/oss_cleaned.csv', 'NAMA_PERUSAHAAN', 'NPWP')
entries_ceisa = process_file('data/raw/ceisa_data.csv', 'data/processed/ceisa_cleaned.csv', 'NAMA_PERUSAHAAN', 'NPWP')

# Save audit
pd.DataFrame(entries_oss + entries_ceisa).to_csv('reports/audit_trail.csv', index=False)
print("Cleansing complete. Results in data/processed/ and reports/audit_trail.csv")
