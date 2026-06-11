import pandas as pd
import numpy as np
from faker import Faker
import random
from datetime import datetime, timedelta
import os

fake = Faker('id_ID')
Faker.seed(42)
random.seed(42)
np.random.seed(42)

# Configuration
TOTAL_UNIQUE = 5000
DUP_NAME = 500
DIFF_NPWP = 250
DIFF_ADDR = 200
CONFLICT_LEGAL = 50
TOTAL_ROWS = TOTAL_UNIQUE + DUP_NAME + DIFF_NPWP + DIFF_ADDR + CONFLICT_LEGAL

# Pools
jenis_perseroan_pool = ['PT', 'CV', 'Firma', 'Perum']
status_hukum_pool = ['TERDAFTAR', 'DISAHKAN', 'PROSES']
status_nib_pool = ['AKTIF', 'DIBEKUKAN', 'DICABUT']
jenis_api_pool = ['API-U', 'API-P']
status_perseroan_pool = ['AKTIF', 'TIDAK AKTIF', 'DIBEKUKAN']

def generate_base_record():
    nib = fake.numerify('############')
    npwp = fake.numerify('###############')
    oss_id = f"OSS-{fake.numerify('#######')}"
    nama_pt = fake.company().upper()
    nama_singkat = nama_pt.replace("PT ", "").replace("CV ", "")[:10].strip()
    
    flag_impor = random.choice([0, 1])
    flag_ekspor = random.choice([0, 1])
    
    return {
        "NIB": nib,
        "NPWP": npwp,
        "OSS_ID": oss_id,
        "NAMA_PERUSAHAAN": nama_pt,
        "NAMA_SINGKATAN": nama_singkat,
        "ALAMAT": fake.street_address().upper(),
        "KELURAHAN": fake.city().upper(), # city as kelurahan replacement for variety
        "DAERAH_ID": f"ID-{random.randint(10, 99)}",
        "KODE_POS": fake.postcode(),
        "NOMOR_TELPON": fake.phone_number(),
        "JENIS_PERSEROAN": random.choice(jenis_perseroan_pool),
        "STATUS_BADAN_HUKUM": random.choice(status_hukum_pool),
        "STATUS_PERSEROAN": random.choice(status_perseroan_pool),
        "FLAG_IMPOR": flag_impor,
        "FLAG_EKSPOR": flag_ekspor,
        "JENIS_API": random.choice(jenis_api_pool) if flag_impor == 1 else None,
        "NOMOR_API": fake.numerify('#####-API') if flag_impor == 1 else None,
        "NIPER": fake.numerify('NIPER-#####') if flag_ekspor == 1 else None,
        "TGL_PERUBAHAN_NIB": datetime(2026, 1, 1) + timedelta(days=random.randint(0, 60)),
        "STATUS_NIB": 'AKTIF'
    }

print(f"Generating {TOTAL_UNIQUE} unique records...")
base_records = [generate_base_record() for _ in range(TOTAL_UNIQUE)]

# Helper to duplicate with changes
def create_variants(count, change_type):
    variants = []
    samples = random.sample(base_records, count)
    for r in samples:
        v = r.copy()
        if change_type == 'name':
            v['NAMA_PERUSAHAAN'] = v['NAMA_PERUSAHAAN'] + " (DUPLICATE)"
        elif change_type == 'npwp':
            v['NPWP'] = fake.numerify('###############') # Different NPWP for same NIB
        elif change_type == 'address':
            v['ALAMAT'] = fake.street_address().upper()
        elif change_type == 'legal':
            v['JENIS_PERSEROAN'] = random.choice([j for j in jenis_perseroan_pool if j != v['JENIS_PERSEROAN']])
        variants.append(v)
    return variants

print("Injecting anomalies...")
name_dups = create_variants(DUP_NAME, 'name')
npwp_diffs = create_variants(DIFF_NPWP, 'npwp')
addr_diffs = create_variants(DIFF_ADDR, 'address')
legal_conflicts = create_variants(CONFLICT_LEGAL, 'legal')

all_data = base_records + name_dups + npwp_diffs + addr_diffs + legal_conflicts
df_master = pd.DataFrame(all_data)

# Inject business anomalies from friend's script
print("Injecting business logic anomalies...")
# Anomali: Flag Aktif tapi NIB Dicabut
df_master.loc[0:5, ['FLAG_EKSPOR', 'STATUS_NIB']] = [1, 'DICABUT']
# Anomali: NIPER ada tapi flag ekspor 0
df_master.loc[10:15, ['NIPER', 'FLAG_EKSPOR']] = ['NIPER-CONFLICT', 0]

# Split into two systems: OSS and CEISA
# OSS has 80% of data, CEISA has 80% of data. Overlap is what we match.
print("Splitting into OSS and CEISA sources...")
idx = df_master.index.tolist()
random.shuffle(idx)

oss_idx = idx[:int(0.8 * TOTAL_ROWS)]
ceisa_idx = idx[int(0.2 * TOTAL_ROWS):]

df_oss = df_master.loc[oss_idx].copy()
df_ceisa = df_master.loc[ceisa_idx].copy()

# Add system-specific noise
# CEISA often has unformatted NPWPs
df_ceisa['NPWP'] = df_ceisa['NPWP'].apply(lambda x: x.replace(".", "").replace("-", "") if pd.notna(x) else x)
# OSS has formal names, CEISA might have messy names
df_ceisa['NAMA_PERUSAHAAN'] = df_ceisa['NAMA_PERUSAHAAN'].apply(lambda x: x.replace("PT ", "") if random.random() > 0.5 else x)

# Rename columns slightly to reflect system differences if needed, but keeping labels for now as per instructions
# Actually, the user list is the TARGET Golden Record list. 
# Systems usually have similar but slightly different names.

# Save
df_oss.to_csv("data/raw/oss_nib_data.csv", index=False)
df_ceisa.to_csv("data/raw/ceisa_data.csv", index=False)
df_master.to_csv("data/raw/dataset_ekspor_raw.csv", index=False)

print(f"✅ Simulation Complete!")
print(f"OSS Records: {len(df_oss)}")
print(f"CEISA Records: {len(df_ceisa)}")
print(f"Master Records (with anomalies): {len(df_master)}")
print(f"Files saved in data/raw/")
