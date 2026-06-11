# [LAB 1] DJBC DATA SIMULATION ENGINE
# Berdasarkan: docs/01_data_dictionary.md & docs/02_business_rules.md

import pandas as pd
import numpy as np
import random
from faker import Faker
from datetime import datetime
from Source.step02_reference import *
from Source.step03_generators import *

# Inisialisasi
fake = Faker('id_ID')
Faker.seed(42)
random.seed(42)

N_MASTER = 5000  # Total perusahaan unik

def run_full_simulation():
    print(f"🚀 Memulai simulasi {N_MASTER} perusahaan (DIRTY MODE)... ")

    # 1. BANGKITKAN MASTER ENTITIES (OSS as Truth) - 16 kolom sesuai data dictionary
    #    KODE_KANTOR ikut dibawa sebagai helper untuk CEISA, di-drop sebelum export OSS
    master_list = []
    for i in range(N_MASTER):
        # 15% NIB Invalid di Master (Validity NIB)
        if random.random() < 0.15:
            nib = generate_nib_invalid()
        else:
            nib = generate_nib_valid()

        npwp = generate_npwp_valid()
        nama = fake.company().upper()
        kppbc = random.choice(KPPBC_LIST)

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
            'KODE_KANTOR': kppbc['kode'],
        })

    df_oss = pd.DataFrame(master_list)

    # --- INJEKSI KEKOTORAN GLOBAL (HEAVY ATTACK) ---
    # 1. Completeness: hanya field opsional yang dikosongkan ("Missing Optional Field").
    #    Field wajib (NIB, NPWP, NAMA, STATUS_NIB) dijamin 100% terisi sesuai business_rules §1.
    for col in ['KELURAHAN_PERSEROAN', 'KODE_POS_PERSEROAN', 'NAMA_SINGKATAN']:
        idx_null = df_oss.sample(frac=0.15).index
        df_oss.loc[idx_null, col] = np.nan

    # 2. Stale Data: sebagian record TGL_PERUBAHAN_NIB sangat lama -> target IS_STALE
    idx_stale_date = df_oss.sample(frac=0.03).index
    df_oss.loc[idx_stale_date, 'TGL_PERUBAHAN_NIB'] = [generate_date_random(2014, 2015) for _ in range(len(idx_stale_date))]

    # 3. Uniqueness: tambah 10% record duplikat persis ("Duplicate Entry")
    df_dups = df_oss.sample(frac=0.10)
    df_oss = pd.concat([df_oss, df_dups], ignore_index=True)

    # 2. CREATE CEISA DATASET (Subset & Heavy Anomaly) - 16 kolom sesuai data dictionary
    df_ceisa = df_oss.sample(frac=0.9).copy()

    # Transformasi kolom: OSS -> CEISA
    df_ceisa = df_ceisa.rename(columns={
        'NPWP_PERSEROAN': 'NPWP',
        'NAMA_PERSEROAN': 'NAMA_PERUSAHAAN',
        'ALAMAT_PERSEROAN': 'ALAMAT_PERUSAHAAN',
        'KELURAHAN_PERSEROAN': 'KELURAHAN',
        'PERSEROAN_DAERAH_ID': 'DAERAH_ID',
        'KODE_POS_PERSEROAN': 'KODE_POS',
        'TGL_PERUBAHAN_NIB': 'TGL_TERBIT_NIB'
    })

    df_ceisa['ID_PERUSAHAAN'] = [f"C{str(i).zfill(6)}" for i in range(len(df_ceisa))]
    df_ceisa['NOMOR_TELPON'] = [fake.phone_number() for _ in range(len(df_ceisa))]
    df_ceisa['KATEGORI'] = random.choices(KATEGORI_CEISA_POOL, k=len(df_ceisa))
    df_ceisa['NIPER'] = [generate_niper_valid() if k != 'IMPORTIR' else "" for k in df_ceisa['KATEGORI']]
    df_ceisa['NOMOR_API'] = [generate_api_valid() if k != 'EKSPORTIR' else "" for k in df_ceisa['KATEGORI']]
    # TGL_SYNC_OSS: tanggal sync terakhir dari OSS - dasar HIGH_SYNC_LAG & data mart dedup
    df_ceisa['TGL_SYNC_OSS'] = [generate_date_recent(90) for _ in range(len(df_ceisa))]

    ceisa_cols = ['ID_PERUSAHAAN', 'NIB', 'NPWP', 'NAMA_PERUSAHAAN', 'ALAMAT_PERUSAHAAN',
                  'KELURAHAN', 'DAERAH_ID', 'KODE_POS', 'NOMOR_TELPON', 'KATEGORI',
                  'NIPER', 'NOMOR_API', 'TGL_TERBIT_NIB', 'STATUS_NIB', 'KODE_KANTOR', 'TGL_SYNC_OSS']
    df_ceisa = df_ceisa[ceisa_cols]

    # 3. INJEKSI ANOMALI BERAT (tahap0_simulation_faker.md §4)
    print("⚠️ Menyuntikkan anomali data tingkat tinggi...")

    # Anomali: Format NPWP - NPWP kotor masif di CEISA (25%)
    idx_npwp = df_ceisa.sample(frac=0.25).index
    df_ceisa.loc[idx_npwp, 'NPWP'] = [generate_npwp_invalid() for _ in range(len(idx_npwp))]

    # Anomali: Typo Nama - fuzzy name di CEISA (15%)
    idx_fuzzy = df_ceisa.sample(frac=0.15).index
    df_ceisa.loc[idx_fuzzy, 'NAMA_PERUSAHAAN'] = df_ceisa.loc[idx_fuzzy, 'NAMA_PERUSAHAAN'].apply(lambda x: str(x).replace("PT ", "") + " (CABANG)")

    # Anomali: Logical Conflict - NIPER (CEISA) terisi padahal FLAG_EKSPOR (OSS) = 'N'
    idx_logic = df_ceisa.sample(frac=0.15).index
    df_ceisa.loc[idx_logic, 'NIPER'] = "4803163678"  # paksa terisi
    df_oss.loc[df_oss.index.isin(idx_logic), 'FLAG_EKSPOR'] = 'N'

    # Anomali: Konflik Status - STATUS_NIB OSS != CEISA -> target IS_OUT_OF_SYNC
    idx_conflict = df_ceisa.sample(n=200).index
    df_ceisa.loc[idx_conflict, 'STATUS_NIB'] = 'AKTIF'
    df_oss.loc[df_oss.index.isin(idx_conflict), 'STATUS_NIB'] = 'DICABUT'

    # Anomali: Data Mart Snapshot Duplicate - NIB sama, snapshot lama dgn NAMA & TGL_SYNC_OSS beda
    idx_snapshot = df_ceisa.sample(frac=0.05).index
    df_snapshot_old = df_ceisa.loc[idx_snapshot].copy()
    df_snapshot_old['NAMA_PERUSAHAAN'] = df_snapshot_old['NAMA_PERUSAHAAN'] + " (OLD)"
    df_snapshot_old['TGL_SYNC_OSS'] = [generate_date_random(2023, 2024) for _ in range(len(df_snapshot_old))]
    df_ceisa = pd.concat([df_ceisa, df_snapshot_old], ignore_index=True)

    # 4. EXPORT DATA
    df_oss = df_oss.drop(columns=['KODE_KANTOR'])  # KODE_KANTOR khusus CEISA sesuai data dictionary
    df_oss.to_csv('data/raw/oss_nib_data.csv', index=False)
    df_ceisa.to_csv('data/raw/ceisa_data.csv', index=False)

    print(f"✅ Simulasi Berhasil (DIRTY DATA READY)!")
    print(f"   - OSS: {len(df_oss)} records")
    print(f"   - CEISA: {len(df_ceisa)} records")

if __name__ == "__main__":
    run_full_simulation()
