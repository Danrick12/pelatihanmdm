#!/usr/bin/env python3
"""
Assemble MDM_Kelompok5_DJBC.ipynb from source .py files.
Reads each source file, wraps into code cells, adds markdown narratives.
Outputs to notebooks/MDM_Kelompok5_DJBC.ipynb.
"""
import json, os, sys, re

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DIR = os.path.join(PROJECT_ROOT, 'Source')
NOTEBOOKS_DIR = os.path.join(PROJECT_ROOT, 'notebooks')
OUTPUT_FILE = os.path.join(NOTEBOOKS_DIR, 'MDM_Kelompok5_DJBC.ipynb')
os.makedirs(NOTEBOOKS_DIR, exist_ok=True)

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def md_cell(text):
    return {"cell_type": "markdown", "metadata": {}, "source": [text]}

def code_cell(text):
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": [text]}

cells = []

# ================================================================
# COVER
# ================================================================
cells.append(md_cell("""# MDM DJBC - Master Data Management

## Single Importer & Exporter View

**Kelompok 5**

Notebook ini mengimplementasikan pipeline Master Data Management (MDM) untuk
mengintegrasikan data dari OSS (Online Single Submission) dan CEISA (Customs
Excise Information System) menjadi Golden Record tunggal per entitas perusahaan.

### Tahapan:
1. **Tahap 0** - Simulasi Data & Faker Engine
2. **Tahap 1** - Data Profiling
3. **Tahap 2** - Data Cleansing & Standardization
4. **Tahap 3** - Duplicate Detection & Matching
5. **Tahap 4** - Golden Record & Survivorship
6. **Tahap 5** - Data Quality Monitoring
7. **Tahap 6** - YData Profiling Dashboard

---

### Narasi Pembuka

**Master Data Management (MDM)** adalah pendekatan strategis untuk mengelola data master
perusahaan. Dalam konteks DJBC, data importir dan eksportir nasional tersebar di dua
sistem utama: **OSS** (sistem perizinan berusaha) dan **CEISA** (sistem operasional
kepabeanan).

Permasalahan utama yang dihadapi:
1. Data tersebar di dua sistem yang tidak terintegrasi
2. Ketidakseragaman format data antar sistem
3. Duplikasi data intra-sistem maupun antar-sistem
4. Konflik data (status berbeda, data usang, dll.)

Pipeline MDM yang diimplementasikan mencakup simulasi data dengan anomali sengaja,
profiling kualitas data, pembersihan dan standardisasi, pencocokan antar sumber,
pembentukan Golden Record, monitoring kualitas, dan dashboard profiling akhir.

> **Catatan:** Notebook ini dirancang untuk Google Colab. Semua library akan diinstall
> otomatis. Data akan disimpan di folder `/content/`."""))

# ================================================================
# CELL: Setup - Instalasi Library
# ================================================================
cells.append(md_cell("""## Setup Environment

### 1. Instalasi Library

Cell pertama menginstall semua library yang dibutuhkan:

| Library | Fungsi |
|---------|--------|
| missingno | Visualisasi missing values |
| faker | Generator data simulasi |
| ydata-profiling | Laporan profiling otomatis |
| fuzzywuzzy, jellyfish | Fuzzy string matching |
| recordlinkage | Framework record linkage |
| networkx | Analisis graf untuk clustering |"""))

cells.append(code_cell("""# Install library untuk Google Colab
import warnings
warnings.filterwarnings('ignore')

!pip install missingno faker ydata-profiling fuzzywuzzy python-Levenshtein jellyfish recordlinkage networkx -q

print('Semua library berhasil diinstall!')"""))

# ================================================================
# CELL: Import Library
# ================================================================
cells.append(md_cell("""### 2. Import Semua Library

Mengimport library yang akan digunakan di seluruh pipeline."""))

cells.append(code_cell(read_file(os.path.join(SOURCE_DIR, 'step01_setup.py')).replace(
    "from Source.step02_reference import *",
    "# Reference data will be defined inline"
).replace(
    "from Source.step03_generators import *",
    "# Generators will be defined inline"
)))

# ================================================================
# CELL: Setup Direktori
# ================================================================
cells.append(md_cell("""### 3. Setup Direktori Google Colab

Membuat struktur folder untuk menyimpan data dan laporan."""))

cells.append(code_cell("""# Setup base path untuk Google Colab
import os

BASE_PATH = '/content'
DATA_RAW = os.path.join(BASE_PATH, 'data/raw')
DATA_PROCESSED = os.path.join(BASE_PATH, 'data/processed')
DATA_GOLDEN = os.path.join(BASE_PATH, 'data/golden')
REPORTS_DIR = os.path.join(BASE_PATH, 'reports')

for d in [DATA_RAW, DATA_PROCESSED, DATA_GOLDEN, REPORTS_DIR]:
    os.makedirs(d, exist_ok=True)

print('Struktur folder siap:')
print(f'  Data mentah   : {DATA_RAW}/')
print(f'  Data bersih   : {DATA_PROCESSED}/')
print(f'  Golden Record : {DATA_GOLDEN}/')
print(f'  Laporan       : {REPORTS_DIR}/')

# Untuk menyimpan permanen di Google Drive, gunakan:
# from google.colab import drive
# drive.mount('/content/drive')
# BASE_PATH = '/content/drive/MyDrive/MDM_DJBC'"""))

# ================================================================
# TAHAP 0: SIMULATION
# ================================================================
cells.append(md_cell("""# TAHAP 0: SIMULASI DATA & FAKER ENGINE

**Tujuan:** Membangkitkan dataset simulasi yang mencerminkan kompleksitas dunia nyata
di DJBC, lengkap dengan anomali untuk menguji sistem MDM.

### Penjelasan

Tahap ini membangkitkan data untuk dua sistem:
1. **OSS** - Sistem perizinan berusaha (System of Record untuk legalitas)
2. **CEISA** - Sistem operasional kepabeanan

**Parameter:** 5.000 perusahaan unit, ~6.000-6.500 total record.

**Anomali yang disuntikkan:**
- NPWP kotor (tanpa separator) di CEISA (25%)
- Typo nama perusahaan (15%)
- NIB invalid (15%)
- Konflik status OSS vs CEISA (200 record)
- Logical conflict (FLAG_EKSPOR=N vs NIPER terisi)
- Duplicate entry OSS (10%)
- Data mart snapshot CEISA (5%)
- Stale data (3%)
- Missing optional fields (15%)"""))

# Refactor step02 and step03 inline
cells.append(md_cell("""### Lab 0.1 - Data Referensi DJBC

Kode referensi standar DJBC: provinsi, KPPBC, enum values."""))

cells.append(code_cell(read_file(os.path.join(SOURCE_DIR, 'step02_reference.py'))))

cells.append(md_cell("""### Lab 0.2 - Generator Identifier DJBC

Fungsi untuk menghasilkan NIB, NPWP, API, NIPER, dan tanggal."""))

cells.append(code_cell(read_file(os.path.join(SOURCE_DIR, 'step03_generators.py'))))

# Simulation engine - need to adapt imports
sim_code = read_file(os.path.join(SOURCE_DIR, 'step04_simulation.py'))
# Fix imports
sim_code = sim_code.replace(
    "from Source.step02_reference import *",
    "# References already defined above"
).replace(
    "from Source.step03_generators import *",
    "# Generators already defined above"
)
# Fix file paths for Colab
sim_code = sim_code.replace(
    "df_oss.to_csv('data/raw/oss_nib_data.csv', index=False)",
    "df_oss.to_csv(f'{DATA_RAW}/oss_nib_data.csv', index=False)"
).replace(
    "df_ceisa.to_csv('data/raw/ceisa_data.csv', index=False)",
    "df_ceisa.to_csv(f'{DATA_RAW}/ceisa_data.csv', index=False)"
)

cells.append(md_cell("""### Lab 1 - DJBC Data Simulation Engine

Fungsi utama simulasi yang membangkitkan data OSS dan CEISA dengan anomali."""))

cells.append(code_cell(sim_code))

# ================================================================
# TAHAP 1: DATA PROFILING
# ================================================================
cells.append(md_cell("""# TAHAP 1: DATA PROFILING

**Tujuan:** Eksplorasi dan pengukuran kualitas data baseline sebelum cleansing/MDM.

### Penjelasan

Lingkup analisis per dataset (OSS & CEISA):
1. Dataset overview (shape, dtype, null, unique)
2. Statistik deskriptif (numerik & kategorik)
3. Missing value analysis (severity + visualisasi)
4. Duplicate analysis (full, by NIB, by NAMA)
5. Format validation (NIB, NPWP, KODE_POS, STATUS_NIB)
6. Baseline DQ Score (4 dimensi DMBOK)
7. Laporan YData Profiling"""))

profiling_code = read_file(os.path.join(SOURCE_DIR, 'step05_profiling.py'))
# Fix imports
profiling_code = profiling_code.replace(
    "from Source.step02_reference import (",
    "# References already defined above\n# from Source.step02_reference import ("
).replace(
    "matplotlib.use('Agg')",
    "# matplotlib.use('Agg')  # Not needed in Colab"
)
# Remove the __main__ section - we'll add it separately
profiling_code = re.sub(r"if __name__ == \"__main__\":.*", "", profiling_code, flags=re.DOTALL)

cells.append(md_cell("""### Fungsi-fungsi Profiling

Fungsi untuk setiap aktivitas profiling yang akan dijalankan."""))

cells.append(code_cell(profiling_code))

cells.append(md_cell("""### Eksekusi Profiling - OSS

Menjalankan profiling untuk dataset OSS."""))

# Split profiling execution into manageable cells
cells.append(code_cell("""# Load data OSS
df_oss = pd.read_csv(f'{DATA_RAW}/oss_nib_data.csv', dtype={'NIB': str, 'NPWP_PERSEROAN': str})
print(f'Dataset OSS: {len(df_oss):,} baris')

dataset_overview(df_oss, 'OSS')
descriptive_stats(df_oss, 'OSS')
missing_oss = missing_value_analysis(df_oss, 'OSS')
dup_oss = duplicate_analysis(df_oss, 'OSS', 'NAMA_PERSEROAN')
fmt_oss = format_validation(df_oss, 'OSS')"""))

cells.append(code_cell("""# Profiling CEISA
df_ceisa = pd.read_csv(f'{DATA_RAW}/ceisa_data.csv', dtype={'NIB': str, 'NPWP': str})
print(f'Dataset CEISA: {len(df_ceisa):,} baris')

dataset_overview(df_ceisa, 'CEISA')
descriptive_stats(df_ceisa, 'CEISA')
missing_ceisa = missing_value_analysis(df_ceisa, 'CEISA')
dup_ceisa = duplicate_analysis(df_ceisa, 'CEISA', 'NAMA_PERUSAHAAN')
fmt_ceisa = format_validation(df_ceisa, 'CEISA')"""))

cells.append(md_cell("""### Baseline Data Quality Score

Menghitung skor kualitas data 4 dimensi DMBOK sebagai baseline."""))

cells.append(code_cell("""# Baseline DQ Score
oss_metrics = calculate_dq_metrics(df_oss, 'OSS')
ceisa_metrics = calculate_dq_metrics(df_ceisa, 'CEISA')

dq_compare = pd.DataFrame({
    'Dimensi': list(oss_metrics.keys()),
    'OSS (%)': [f'{oss_metrics[k]:.2f}%' for k in oss_metrics],
    'CEISA (%)': [f'{ceisa_metrics[k]:.2f}%' for k in ceisa_metrics],
})
display(dq_compare)

avg_oss = sum(oss_metrics.values()) / len(oss_metrics)
avg_ceisa = sum(ceisa_metrics.values()) / len(ceisa_metrics)
print(f'\\nOverall DQ Score:')
print(f'  OSS   : {avg_oss:.2f}%')
print(f'  CEISA : {avg_ceisa:.2f}%')

# Visualisasi radar chart
fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
dims = list(oss_metrics.keys())
angles = np.linspace(0, 2*np.pi, len(dims), endpoint=False).tolist() + [0]
oss_vals = list(oss_metrics.values()) + [list(oss_metrics.values())[0]]
ceisa_vals = list(ceisa_metrics.values()) + [list(ceisa_metrics.values())[0]]

ax.plot(angles, oss_vals, 'o-', lw=2, color='#1565C0', label='OSS')
ax.fill(angles, oss_vals, alpha=0.1, color='#1565C0')
ax.plot(angles, ceisa_vals, 'o-', lw=2, color='#F44336', label='CEISA')
ax.fill(angles, ceisa_vals, alpha=0.1, color='#F44336')
ax.set_xticks(angles[:-1])
ax.set_xticklabels(dims, fontsize=11, fontweight='bold')
ax.set_ylim(0, 100)
ax.set_title('Baseline DQ Score - OSS vs CEISA', fontsize=14, fontweight='bold', pad=20)
ax.legend(loc='upper right', bbox_to_anchor=(1.2, 1.1))
plt.tight_layout()
plt.savefig(f'{REPORTS_DIR}/dq_baseline.png', dpi=150, bbox_inches='tight')
plt.show()"""))

cells.append(md_cell("""### Laporan YData Profiling

Menghasilkan laporan profiling interaktif untuk OSS dan CEISA."""))

cells.append(code_cell("""# YData Profiling Reports
print('Membuat YData Profiling untuk OSS...')
ProfileReport(
    df_oss,
    title='Data Profiling Report - OSS (Before MDM)',
    explorative=True,
    correlations={"auto": {"calculate": False}, "pearson": {"calculate": True},
                  "spearman": {"calculate": False}, "kendall": {"calculate": False},
                  "phi_k": {"calculate": False}, "cramers": {"calculate": False}},
    interactions={"continuous": False}
).to_file(f'{REPORTS_DIR}/profiling_before_oss.html')
print(f'  Report OSS: {REPORTS_DIR}/profiling_before_oss.html')

print('\\nMembuat YData Profiling untuk CEISA...')
ProfileReport(
    df_ceisa,
    title='Data Profiling Report - CEISA (Before MDM)',
    explorative=True,
    correlations={"auto": {"calculate": False}, "pearson": {"calculate": True},
                  "spearman": {"calculate": False}, "kendall": {"calculate": False},
                  "phi_k": {"calculate": False}, "cramers": {"calculate": False}},
    interactions={"continuous": False}
).to_file(f'{REPORTS_DIR}/profiling_before_ceisa.html')
print(f'  Report CEISA: {REPORTS_DIR}/profiling_before_ceisa.html')
print('\\nTahap 1 - Data Profiling selesai!')"""))

# ================================================================
# TAHAP 2: DATA CLEANSING
# ================================================================
cells.append(md_cell("""# TAHAP 2: DATA CLEANSING & STANDARDIZATION

**Tujuan:** Membersihkan dan menstandarisasi data OSS & CEISA agar konsisten.

### Penjelasan

Kegiatan:
1. AuditTrail - catat setiap operasi cleansing
2. Standardisasi NAMA - uppercase, normalisasi prefix
3. Standardisasi ALAMAT - title case, normalisasi singkatan
4. Standardisasi identifier - NIB, NPWP, KODE_POS, Telepon
5. CEISA Data Mart Dedup - 1 baris per NIB (snapshot terbaru)
6. Missing value handling - flag field wajib
7. Validasi referensial - kode wilayah
8. Quality Gate - pemeriksaan otomatis"""))

cleansing_code = read_file(os.path.join(SOURCE_DIR, 'step06_cleansing.py'))
# Fix imports
cleansing_code = re.sub(
    r"from Source\.step02_reference import PROVINSI",
    "# PROVINSI already defined above",
    cleansing_code
)
cleansing_code = re.sub(
    r"from Source\.step05_profiling import\s+NIB_PATTERN, NPWP_PATTERN, calculate_dq_metrics",
    "# NIB_PATTERN, NPWP_PATTERN, calculate_dq_metrics already defined above",
    cleansing_code
)
# Fix DUMMY_NIB reference
cleansing_code = cleansing_code.replace(
    "from Source.step07_matching import extract_digits, normalize_for_matching, DUMMY_NIB",
    "# These will be defined in Tahap 3, using local DUMMY_NIB"
)
# Fix file paths
cleansing_code = re.sub(
    r"pd\.read_csv\('data/raw/oss_nib_data.csv'",
    "pd.read_csv(f'{DATA_RAW}/oss_nib_data.csv'",
    cleansing_code
)
cleansing_code = re.sub(
    r"pd\.read_csv\('data/raw/ceisa_data.csv'",
    "pd.read_csv(f'{DATA_RAW}/ceisa_data.csv'",
    cleansing_code
)
cleansing_code = re.sub(
    r"df_oss\.to_csv\('data/processed/oss_cleaned.csv'",
    "df_oss.to_csv(f'{DATA_PROCESSED}/oss_cleaned.csv'",
    cleansing_code
)
cleansing_code = re.sub(
    r"df_ceisa\.to_csv\('data/processed/ceisa_cleaned.csv'",
    "df_ceisa_clean.to_csv(f'{DATA_PROCESSED}/ceisa_cleaned.csv'" if 'df_ceisa_clean' in cleansing_code else "df_ceisa.to_csv(f'{DATA_PROCESSED}/ceisa_cleaned.csv'",
    cleansing_code
)
cleansing_code = re.sub(
    r"df_clean\.to_csv\('data/processed/dataset_clean.csv'",
    "df_clean.to_csv(f'{DATA_PROCESSED}/dataset_clean.csv'",
    cleansing_code
)
cleansing_code = re.sub(
    r"audit\.to_dataframe\(\)\.to_csv\('reports/audit_trail.csv'",
    "audit.to_dataframe().to_csv(f'{REPORTS_DIR}/audit_trail.csv'",
    cleansing_code
)

# Remove __main__ section
cleansing_code = re.sub(r"if __name__ == \"__main__\":.*", "", cleansing_code, flags=re.DOTALL)

cells.append(code_cell(cleansing_code))

# ================================================================
# TAHAP 3: DUPLICATE DETECTION & MATCHING
# ================================================================
cells.append(md_cell("""# TAHAP 3: DUPLICATE DETECTION & MATCHING

**Tujuan:** Mencocokkan data OSS dan CEISA untuk mengidentifikasi entitas yang sama.

### Penjelasan

Prioritas matching:
1. Exact match NIB (Prioritas 1)
2. Exact match NPWP (Prioritas 2)
3. Fuzzy match nama + alamat (Prioritas 3)
4. Composite similarity score (NPWP 20% + Nama 50% + Alamat 30%)
5. Duplicate clustering internal"""))

# Read step07 - handle the fact that it's a large file
matching_code = read_file(os.path.join(SOURCE_DIR, 'step07_matching.py'))

# Fix file paths
matching_code = matching_code.replace(
    "pd.read_csv('data/processed/oss_cleaned.csv'",
    "pd.read_csv(f'{DATA_PROCESSED}/oss_cleaned.csv'"
).replace(
    "pd.read_csv('data/processed/ceisa_cleaned.csv'",
    "pd.read_csv(f'{DATA_PROCESSED}/ceisa_cleaned.csv'"
).replace(
    "candidate_pairs.to_csv('reports/candidate_pairs.csv'",
    "candidate_pairs.to_csv(f'{REPORTS_DIR}/candidate_pairs.csv'"
).replace(
    "df_clusters.to_csv('reports/duplicate_cluster.csv'",
    "df_clusters.to_csv(f'{REPORTS_DIR}/duplicate_cluster.csv'"
).replace(
    "plot_score_distribution(df_fuzzy, output_path='reports/composite_score_distribution.png'",
    "plot_score_distribution(df_fuzzy, output_path=f'{REPORTS_DIR}/composite_score_distribution.png'"
)

# Remove __main__
matching_code = re.sub(r"if __name__ == \"__main__\":.*", "", matching_code, flags=re.DOTALL)

cells.append(code_cell(matching_code))

# ================================================================
# TAHAP 4: GOLDEN RECORD
# ================================================================
cells.append(md_cell("""# TAHAP 4: GOLDEN RECORD & SURVIVORSHIP

**Tujuan:** Membentuk satu Golden Record per entitas dari gabungan OSS dan CEISA.

### Penjelasan

Aturan survivorship:
- OSS menang untuk data legalitas (System of Record)
- CEISA menang untuk data operasional
- Orphan records tetap masuk dengan SOURCE=OSS_ONLY/CEISA_ONLY"""))

golden_code = read_file(os.path.join(SOURCE_DIR, 'step08_golden_record.py'))
# Fix imports
golden_code = golden_code.replace(
    "from Source.step07_matching import extract_digits, normalize_for_matching, DUMMY_NIB",
    "# extract_digits, normalize_for_matching, DUMMY_NIB already defined"
).replace(
    "from Source.step02_reference import STATUS_NIB_POOL",
    "# STATUS_NIB_POOL already defined"
).replace(
    "from fuzzywuzzy import fuzz",
    "# fuzz already imported"
)
# Fix paths
golden_code = re.sub(
    r"pd\.read_csv\('data/processed/oss_cleaned\.csv'",
    "pd.read_csv(f'{DATA_PROCESSED}/oss_cleaned.csv'",
    golden_code
)
golden_code = re.sub(
    r"pd\.read_csv\('data/processed/ceisa_cleaned\.csv'",
    "pd.read_csv(f'{DATA_PROCESSED}/ceisa_cleaned.csv'",
    golden_code
)
golden_code = re.sub(
    r"pd\.read_csv\('reports/candidate_pairs\.csv'",
    "pd.read_csv(f'{REPORTS_DIR}/candidate_pairs.csv'",
    golden_code
)
golden_code = re.sub(
    r"pd\.read_csv\('reports/duplicate_cluster\.csv'",
    "pd.read_csv(f'{REPORTS_DIR}/duplicate_cluster.csv'",
    golden_code
)
golden_code = re.sub(
    r"df_golden\.to_csv\('data/golden/golden_record\.csv'",
    "df_golden.to_csv(f'{DATA_GOLDEN}/golden_record.csv'",
    golden_code
)
golden_code = re.sub(
    r"df_provenance\.to_csv\('reports/provenance_log\.csv'",
    "df_provenance.to_csv(f'{REPORTS_DIR}/provenance_log.csv'",
    golden_code
)
golden_code = re.sub(
    r"df_conflicts\.to_csv\('reports/conflict_log\.csv'",
    "df_conflicts.to_csv(f'{REPORTS_DIR}/conflict_log.csv'",
    golden_code
)
# Remove __main__
golden_code = re.sub(r"if __name__ == \"__main__\":.*", "", golden_code, flags=re.DOTALL)

cells.append(code_cell(golden_code))

# ================================================================
# TAHAP 5: DQ MONITORING
# ================================================================
cells.append(md_cell("""# TAHAP 5: DATA QUALITY MONITORING

**Tujuan:** Mengukur dan membandingkan kualitas data Before vs After MDM.

### Penjelasan

5 dimensi DMBOK: Completeness, Validity, Uniqueness, Consistency, Timeliness.
Dijalankan pada 3 dataset: OSS, CEISA, Golden Record."""))

dq_code = read_file(os.path.join(SOURCE_DIR, 'step09_quality_monitoring.py'))
# Fix imports
dq_code = dq_code.replace(
    "from Source.step02_reference import STATUS_NIB_POOL, JENIS_PERSEROAN_POOL, KATEGORI_CEISA_POOL",
    "# Already defined above"
).replace(
    "from Source.step07_matching import DUMMY_NIB",
    "# DUMMY_NIB already defined"
)
# Fix paths
dq_code = re.sub(
    r"pd\.read_csv\('data/processed/oss_cleaned\.csv'",
    "pd.read_csv(f'{DATA_PROCESSED}/oss_cleaned.csv'",
    dq_code
)
dq_code = re.sub(
    r"pd\.read_csv\('data/processed/ceisa_cleaned\.csv'",
    "pd.read_csv(f'{DATA_PROCESSED}/ceisa_cleaned.csv'",
    dq_code
)
dq_code = re.sub(
    r"pd\.read_csv\('data/golden/golden_record\.csv'",
    "pd.read_csv(f'{DATA_GOLDEN}/golden_record.csv'",
    dq_code
)
dq_code = re.sub(
    r"df_scorecard\.to_csv\('reports/dq_scorecard\.csv'",
    "df_scorecard.to_csv(f'{REPORTS_DIR}/dq_scorecard.csv'",
    dq_code
)
dq_code = re.sub(
    r"df_results\.to_csv\('reports/dq_rule_results\.csv'",
    "df_results.to_csv(f'{REPORTS_DIR}/dq_rule_results.csv'",
    dq_code
)
# Remove __main__
dq_code = re.sub(r"if __name__ == \"__main__\":.*", "", dq_code, flags=re.DOTALL)

cells.append(code_cell(dq_code))

# ================================================================
# TAHAP 6: YDATA PROFILING DASHBOARD
# ================================================================
cells.append(md_cell("""# TAHAP 6: YDATA PROFILING DASHBOARD

**Tujuan:** Profiling ulang Golden Record dan perbandingan Before vs After MDM.

### Penjelasan

1. YData Profiling pada Golden Record
2. Perbandingan metrik: jumlah record, missing value, validitas, duplikasi
3. Insight bisnis dan rekomendasi data governance"""))

dashboard_code = read_file(os.path.join(SOURCE_DIR, 'step10_profiling_dashboard.py'))
# Fix imports
dashboard_code = dashboard_code.replace(
    "from Source.step05_profiling import",
    "# Already defined above\n# from Source.step05_profiling import"
).replace(
    "from Source.step07_matching import DUMMY_NIB",
    "# DUMMY_NIB already defined"
)
# Fix paths
dashboard_code = re.sub(
    r"pd\.read_csv\('data/raw/oss_nib_data\.csv'",
    "pd.read_csv(f'{DATA_RAW}/oss_nib_data.csv'",
    dashboard_code
)
dashboard_code = re.sub(
    r"pd\.read_csv\('data/raw/ceisa_data\.csv'",
    "pd.read_csv(f'{DATA_RAW}/ceisa_data.csv'",
    dashboard_code
)
dashboard_code = re.sub(
    r"pd\.read_csv\('data/golden/golden_record\.csv'",
    "pd.read_csv(f'{DATA_GOLDEN}/golden_record.csv'",
    dashboard_code
)
dashboard_code = re.sub(
    r"profile\.to_file\('reports/profiling_after\.html'",
    "profile.to_file(f'{REPORTS_DIR}/profiling_after.html'",
    dashboard_code
)
# Remove __main__
dashboard_code = re.sub(r"if __name__ == \"__main__\":.*", "", dashboard_code, flags=re.DOTALL)

cells.append(code_cell(dashboard_code))

# ================================================================
# CELL: PENUTUP
# ================================================================
cells.append(md_cell("""# SELESAI!

## Pipeline MDM End-to-End Berhasil Dijalankan

**Tahap 0** - Simulasi Data & Faker Engine
**Tahap 1** - Data Profiling (Baseline DQ)
**Tahap 2** - Data Cleansing & Standardization
**Tahap 3** - Duplicate Detection & Matching
**Tahap 4** - Golden Record & Survivorship
**Tahap 5** - Data Quality Monitoring
**Tahap 6** - YData Profiling Dashboard

### Struktur Output

```
/content/
data/
  raw/oss_nib_data.csv, ceisa_data.csv
  processed/oss_cleaned.csv, ceisa_cleaned.csv, dataset_clean.csv
  golden/golden_record.csv
reports/
  profiling_before_oss.html, profiling_before_ceisa.html
  profiling_after.html
  audit_trail.csv, provenance_log.csv, conflict_log.csv
  dq_scorecard.csv, dq_rule_results.csv
  *.png
```

**Mini Project - Master Data Management DJBC**
**Kelompok 5 | Single Importer & Exporter View**"""))

# ================================================================
# BUILD AND SAVE NOTEBOOK
# ================================================================
notebook = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.10.0"},
        "colab": {"name": "MDM_Kelompok5_DJBC.ipynb", "provenance": []}
    },
    "cells": cells
}

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    json.dump(notebook, f, indent=2, ensure_ascii=False)

print(f'Notebook created: {OUTPUT_FILE}')
print(f'Cells: {len(cells)} ({sum(1 for c in cells if c["cell_type"]=="markdown")} markdown + {sum(1 for c in cells if c["cell_type"]=="code")} code)')
print(f'File size: {os.path.getsize(OUTPUT_FILE):,} bytes')
