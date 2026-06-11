# [LAB 4] MATCHING (TAHAP 3)
# Exact Match on NIB
matches = pd.merge(
    df_oss_clean, 
    df_ceisa_clean, 
    on='NIB', 
    how='inner', 
    suffixes=('_OSS', '_CEISA')
)
print(f'✅ Lab 4: Matching Selesai. Ditemukan {len(matches)} pasangan match.')
