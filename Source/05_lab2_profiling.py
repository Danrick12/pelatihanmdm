# [LAB 2] DATA PROFILING (TAHAP 1)
# Berdasarkan: docs/tahapan/tahap1_data_profiling.md
# Tujuan: Mendeteksi anomali awal sebelum masuk ke tahap Cleansing.

def calculate_baseline_dq(df, dataset_name="OSS"):
    """Menghitung skor kualitas data dasar (Baseline DQ Score)"""
    n_rows = len(df)
    
    # 1. Completeness (Mandatory Fields)
    # NIB, NPWP, NAMA, STATUS_NIB adalah field wajib
    mand_cols = ['NIB', 'STATUS_NIB']
    if dataset_name == "OSS":
        mand_cols += ['NPWP_PERSEROAN', 'NAMA_PERSEROAN']
    else:
        mand_cols += ['NPWP', 'NAMA_PERUSAHAAN']
        
    completeness = (1 - df[mand_cols].isnull().any(axis=1).sum() / n_rows) * 100
    
    # 2. Validity (Format Validation)
    # NIB must be 13 digits
    valid_nib = df['NIB'].astype(str).str.match(r'^\d{13}$').mean() * 100
    
    # NPWP format XX.XXX.XXX.X-XXX.XXX
    npwp_col = 'NPWP_PERSEROAN' if dataset_name == "OSS" else 'NPWP'
    valid_npwp = df[npwp_col].astype(str).str.match(r'^\d{2}\.\d{3}\.\d{3}\.\d{1}-\d{3}\.\d{3}$').mean() * 100
    
    # 3. Uniqueness
    uniqueness = (df['NIB'].nunique() / n_rows) * 100
    
    dq_results = {
        'Dataset': dataset_name,
        'Completeness': f"{completeness:.2f}%",
        'Validity_NIB': f"{valid_nib:.2f}%",
        'Validity_NPWP': f"{valid_npwp:.2f}%",
        'Uniqueness': f"{uniqueness:.2f}%"
    }
    return dq_results

def run_advanced_profiling(df, title="OSS Data"):
    print(f"\n" + "="*50)
    print(f"📊 ADVANCED PROFILING: {title}")
    print("="*50)
    
    # 1. Dataset Overview
    print(f"\n[1] OVERVIEW")
    print(f"- Total Records: {len(df)}")
    print(f"- Total Columns: {len(df.columns)}")
    
    # 2. Missing Value Analysis
    missing_data = df.isnull().sum()
    missing_pct = (missing_data / len(df)) * 100
    print(f"\n[2] MISSING VALUES (%)")
    for col, pct in missing_pct.items():
        if pct > 0:
            severity = "OK" if pct < 5 else "MEDIUM" if pct < 15 else "HIGH"
            print(f"  - {col:20}: {pct:6.2f}% | Severity: {severity}")
        else:
            print(f"  - {col:20}: 0.00%")

    # 3. Duplicate Analysis (NIB)
    n_dup_nib = df.duplicated(subset=['NIB']).sum()
    print(f"\n[3] DUPLICATE ANALYSIS")
    print(f"- Duplicate NIB: {n_dup_nib} records ({(n_dup_nib/len(df))*100:.2f}%)")
    
    # 4. Format Validation Summary
    print(f"\n[4] FORMAT VALIDATION")
    dq = calculate_baseline_dq(df, "OSS" if "OSS" in title else "CEISA")
    for k, v in dq.items():
        if k != 'Dataset': print(f"- {k:15}: {v}")

    # 5. Visualisasi Missingno
    msno.matrix(df)
    plt.title(f"Missing Value Matrix - {title}")
    plt.show()

# --- EKSEKUSI PROFILING ---
# Diasumsikan df_oss dan df_ceisa sudah ada dari Lab 1
try:
    run_advanced_profiling(df_oss, "OSS Dataset (Before Cleansing)")
    run_advanced_profiling(df_ceisa, "CEISA Dataset (Before Cleansing)")
    
    # Optional: Generate YData Profiling jika diperlukan (Tahap 6)
    # from ydata_profiling import ProfileReport
    # profile = ProfileReport(df_oss, title="OSS Profiling Before")
    # profile.to_file("reports/profiling_before_oss.html")
except NameError:
    print("❌ Error: df_oss atau df_ceisa tidak ditemukan. Jalankan Lab 1 terlebih dahulu.")
