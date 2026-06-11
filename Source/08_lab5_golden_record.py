# [LAB 5] GOLDEN RECORD (TAHAP 4)
golden_record = pd.DataFrame({
    'NIB': matches['NIB'],
    'NPWP': matches['NPWP_CLEAN_OSS'], # Priority OSS
    'NAMA_PERUSAHAAN': matches['NAMA_CLEAN_OSS'],
    'SOURCE': 'OSS_CEISA'
})
print(f'✅ Lab 5: Golden Record Terbentuk ({len(golden_record)} rows).')
