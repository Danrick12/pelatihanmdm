# [LAB 1] DJBC DATA SIMULATION ENGINE
# Berdasarkan: docs/01_data_dictionary.md & docs/02_business_rules.md

import pandas as pd
import numpy as np
import random
from faker import Faker
from datetime import datetime
from Source.02_lab0_reference import *
from Source.03_lab0_generators import *

# Inisialisasi
fake = Faker('id_ID')
Faker.seed(42)
random.seed(42)

N_MASTER = 5000  # Total perusahaan unik

def run_full_simulation():
    print(f"🚀 Memulai simulasi {N_MASTER} perusahaan...")
    
    # 1. BANGKITKAN MASTER ENTITIES (OSS as Truth)
    master_list = []
    for i in range(N_MASTER):
        nib = generate_nib_valid()
        npwp = generate_npwp_valid()
        nama = fake.company().upper()
        kppbc = random.choice(KPPBC_LIST)
        
        # Aturan Logika: Jika Impor Y, maka API harus ada
        flag_impor = random.choice(['Y', 'N'])
        jenis_api = random.choice(JENIS_API_POOL) if flag_impor == 'Y' else ""
        
        master_list.append({
            'NIB': nib,
            'NPWP_PERSEROAN': npwp,
            'NAMA_PERSEROAN': nama,
            'NAMA_SINGKATAN': nama.split()[0][:5],
            'JENIS_PERSEROAN': random.choice(JENIS_PERSEROAN_POOL),
            'STATUS_BADAN_HUKUM': random.choice(STATUS_BADAN_HUKUM_POOL),
            'STATUS_PERSEROAN': random.choice(STATUS_PERSEROAN_POOL),
            'ALAMAT_PERSEROAN': fake.street_address().upper(),
            'KELURAHAN_PERSEROAN': fake.city().upper(),
            'PERSEROAN_DAERAH_ID': kppbc['wilayah'],
            'KODE_POS_PERSEROAN': fake.postcode(),
            'FLAG_IMPOR': flag_impor,
            'FLAG_EKSPOR': random.choice(['Y', 'N']),
            'JENIS_API': jenis_api,
            'TGL_PERUBAHAN_NIB': generate_date_random(2023, 2025),
            'STATUS_NIB': random.choices(STATUS_NIB_POOL, weights=[80, 10, 10])[0],
            'FLAG_MITA': random.choice(['Y', 'N']),
            'FLAG_AEO': random.choice(['Y', 'N']),
            'KODE_KANTOR': kppbc['kode']
        })
    
    df_oss = pd.DataFrame(master_list)
    
    # 2. CREATE CEISA DATASET (Subset & Anomaly)
    # Ambil 90% dari master sebagai irisan, sisanya orphan
    df_ceisa = df_oss.sample(frac=0.9).copy()
    
    # Transformasi kolom sesuai skema CEISA (01_data_dictionary §2)
    df_ceisa = df_ceisa.rename(columns={
        'NPWP_PERSEROAN': 'NPWP',
        'NAMA_PERSEROAN': 'NAMA_PERUSAHAAN',
        'ALAMAT_PERSEROAN': 'ALAMAT_PERUSAHAAN',
        'KELURAHAN_PERSEROAN': 'KELURAHAN',
        'PERSEROAN_DAERAH_ID': 'DAERAH_ID',
        'KODE_POS_PERSEROAN': 'KODE_POS',
        'TGL_PERUBAHAN_NIB': 'TGL_TERBIT_NIB'
    })
    
    # Tambah kolom unik CEISA
    df_ceisa['ID_PERUSAHAAN'] = [f"C{str(i).zfill(6)}" for i in range(len(df_ceisa))]
    df_ceisa['NOMOR_TELPON'] = [fake.phone_number() for _ in range(len(df_ceisa))]
    df_ceisa['KATEGORI'] = random.choices(KATEGORI_CEISA_POOL, k=len(df_ceisa))
    df_ceisa['NIPER'] = [generate_niper_valid() if k != 'IMPORTIR' else "" for k in df_ceisa['KATEGORI']]
    df_ceisa['NOMOR_API'] = [generate_api_valid() if k != 'EKSPORTIR' else "" for k in df_ceisa['KATEGORI']]
    
    # Filter kolom CEISA (15 kolom)
    ceisa_cols = ['ID_PERUSAHAAN', 'NIB', 'NPWP', 'NAMA_PERUSAHAAN', 'ALAMAT_PERUSAHAAN', 
                  'KELURAHAN', 'DAERAH_ID', 'KODE_POS', 'NOMOR_TELPON', 'KATEGORI', 
                  'NIPER', 'NOMOR_API', 'TGL_TERBIT_NIB', 'STATUS_NIB', 'KODE_KANTOR']
    df_ceisa = df_ceisa[ceisa_cols]

    # 3. INJEKSI ANOMALI (Business Rules §4)
    print("⚠️ Menyuntikkan anomali data...")
    
    # Anomali 1: NPWP Kotor di CEISA (10%)
    idx_npwp = df_ceisa.sample(frac=0.1).index
    df_ceisa.loc[idx_npwp, 'NPWP'] = df_ceisa.loc[idx_npwp, 'NPWP'].str.replace(r'[\.\-]', '', regex=True)
    
    # Anomali 2: Fuzzy Name di CEISA (5%)
    idx_fuzzy = df_ceisa.sample(frac=0.05).index
    df_ceisa.loc[idx_fuzzy, 'NAMA_PERUSAHAAN'] = df_ceisa.loc[idx_fuzzy, 'NAMA_PERUSAHAAN'].apply(lambda x: x.replace("PT ", "") + " (KANTOR CABANG)")

    # Anomali 3: NIB Typo di CEISA (2%)
    idx_nib = df_ceisa.sample(frac=0.02).index
    df_ceisa.loc[idx_nib, 'NIB'] = df_ceisa.loc[idx_nib, 'NIB'].apply(lambda x: x[:-1] + ('0' if x[-1]!='0' else '1'))

    # Anomali 4: CEISA Out-of-Sync (Status NIB beda)
    idx_stale = df_ceisa.sample(n=50).index
    df_ceisa.loc[idx_stale, 'STATUS_NIB'] = 'AKTIF'
    df_oss.loc[idx_stale, 'STATUS_NIB'] = 'DICABUT'

    # 4. EXPORT DATA
    df_oss.to_csv('data/raw/oss_nib_data.csv', index=False)
    df_ceisa.to_csv('data/raw/ceisa_data.csv', index=False)
    
    print(f"✅ Simulasi Berhasil!")
    print(f"   - OSS: {len(df_oss)} records")
    print(f"   - CEISA: {len(df_ceisa)} records")

if __name__ == "__main__":
    run_full_simulation()
