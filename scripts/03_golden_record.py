import pandas as pd

# Load cleaned data
df_oss = pd.read_csv('data/processed/oss_cleaned.csv', dtype={'NIB': str})
df_ceisa = pd.read_csv('data/processed/ceisa_cleaned.csv', dtype={'NIB': str})

# Normalize identifiers for matching
df_oss['NIB_M'] = df_oss['NIB'].str.strip()
df_ceisa['NIB_M'] = df_ceisa['NIB'].str.strip()

# Step 1: Matching
# Join on NIB (Primary)
match_nib = pd.merge(
    df_oss,
    df_ceisa,
    on='NIB_M',
    how='inner',
    suffixes=('_OSS', '_CEISA')
)

print(f"Matched by NIB: {len(match_nib)}")

# Step 2: Survivorship
# Priority:
# - Identity (Name, NPWP, Address, etc.) -> OSS (Legal Source)
# - Customs Specific (NIPER, API) -> CEISA (Operational Source)

golden_list = []

for _, row in match_nib.iterrows():
    golden = {
        "NIB": row['NIB_OSS'],
        "NPWP": row['NPWP_CLEAN_OSS'], # OSS is legal source for NPWP
        "OSS_ID": row['OSS_ID_OSS'],
        "NAMA_PERUSAHAAN": row['NAMA_PERUSAHAAN_CLEAN_OSS'],
        "NAMA_SINGKATAN": row['NAMA_SINGKATAN_OSS'],
        "ALAMAT": row['ALAMAT_CLEAN_OSS'],
        "KELURAHAN": row['KELURAHAN_OSS'],
        "DAERAH_ID": row['DAERAH_ID_OSS'],
        "KODE_POS": row['KODE_POS_OSS'],
        "NOMOR_TELPON": row['NOMOR_TELPON_OSS'],
        "JENIS_PERSEROAN": row['JENIS_PERSEROAN_OSS'],
        "STATUS_BADAN_HUKUM": row['STATUS_BADAN_HUKUM_OSS'],
        "STATUS_PERSEROAN": row['STATUS_PERSEROAN_OSS'],
        "FLAG_IMPOR": row['FLAG_IMPOR_CEISA'], # Customs flag might be more recent in CEISA
        "FLAG_EKSPOR": row['FLAG_EKSPOR_CEISA'],
        "JENIS_API": row['JENIS_API_CEISA'],
        "NOMOR_API": row['NOMOR_API_CEISA'],
        "NIPER": row['NIPER_CEISA'],
        "TGL_PERUBAHAN_NIB": row['TGL_PERUBAHAN_NIB_OSS'],
        "STATUS_NIB": row['STATUS_NIB_OSS']
    }
    golden_list.append(golden)

# Add records that are ONLY in one system (Non-matched)
matched_nibs = match_nib['NIB_M'].unique()
oss_only = df_oss[~df_oss['NIB_M'].isin(matched_nibs)]
ceisa_only = df_ceisa[~df_ceisa['NIB_M'].isin(matched_nibs)]

for _, row in oss_only.iterrows():
    golden = {c: row.get(c + '_CLEAN', row.get(c)) for c in [
        "NIB", "NPWP", "OSS_ID", "NAMA_PERUSAHAAN", "NAMA_SINGKATAN", 
        "ALAMAT", "KELURAHAN", "DAERAH_ID", "KODE_POS", "NOMOR_TELPON", 
        "JENIS_PERSEROAN", "STATUS_BADAN_HUKUM", "STATUS_PERSEROAN", 
        "FLAG_IMPOR", "FLAG_EKSPOR", "JENIS_API", "NOMOR_API", "NIPER", 
        "TGL_PERUBAHAN_NIB", "STATUS_NIB"
    ]}
    golden_list.append(golden)

for _, row in ceisa_only.iterrows():
    golden = {c: row.get(c + '_CLEAN', row.get(c)) for c in [
        "NIB", "NPWP", "OSS_ID", "NAMA_PERUSAHAAN", "NAMA_SINGKATAN", 
        "ALAMAT", "KELURAHAN", "DAERAH_ID", "KODE_POS", "NOMOR_TELPON", 
        "JENIS_PERSEROAN", "STATUS_BADAN_HUKUM", "STATUS_PERSEROAN", 
        "FLAG_IMPOR", "FLAG_EKSPOR", "JENIS_API", "NOMOR_API", "NIPER", 
        "TGL_PERUBAHAN_NIB", "STATUS_NIB"
    ]}
    golden_list.append(golden)

df_golden = pd.DataFrame(golden_list)

# Final Unique Check on NIB
df_golden = df_golden.drop_duplicates(subset=['NIB'], keep='first')

df_golden.to_csv('data/golden/golden_record_djbc.csv', index=False)
print(f"Golden Record complete: {len(df_golden)} records.")
print("Saved to data/golden/golden_record_djbc.csv")
