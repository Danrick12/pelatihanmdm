# [LAB 3] CLEANSING (TAHAP 2)
def clean_data(df):
    df_c = df.copy()
    # Standardize NPWP
    df_c['NPWP_CLEAN'] = df_c['NPWP'].apply(lambda x: re.sub(r'\D', '', str(x)))
    # Standardize Nama
    df_c['NAMA_CLEAN'] = df_c['NAMA_PERUSAHAAN'].str.upper().str.strip()
    return df_c

df_oss_clean = clean_data(df_oss)
df_ceisa_clean = clean_data(df_ceisa)
print('✅ Lab 3: Cleansing Selesai.')
