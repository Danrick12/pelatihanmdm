#!/usr/bin/env python3
"""
Rebuild MDM_Kelompok5_DJBC.ipynb from scratch.
Reads source .py files, wraps into code cells, adds execution cells,
fixes paths for Colab, adds markdown narratives.
"""
import json, os, re, sys

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

def fix_paths(code):
    """Fix all hardcoded data/reports paths to use Colab variables"""
    code = re.sub(r"'data/raw/([^']+)'", r"f'{DATA_RAW}/\\1'", code)
    code = re.sub(r"'data/processed/([^']+)'", r"f'{DATA_PROCESSED}/\\1'", code)
    code = re.sub(r"'data/golden/([^']+)'", r"f'{DATA_GOLDEN}/\\1'", code)
    code = re.sub(r"'reports/([^']+)'", r"f'{REPORTS_DIR}/\\1'", code)
    # Also fix double-quoted paths
    code = re.sub(r'"data/raw/([^"]+)"', r"f'{DATA_RAW}/\\1'", code)
    code = re.sub(r'"data/processed/([^"]+)"', r"f'{DATA_PROCESSED}/\\1'", code)
    code = re.sub(r'"data/golden/([^"]+)"', r"f'{DATA_GOLDEN}/\\1'", code)
    code = re.sub(r'"reports/([^"]+)"', r"f'{REPORTS_DIR}/\\1'", code)
    return code

def remove_main_section(code):
    """Remove if __name__ == '__main__' block but keep the code inside"""
    pattern = r"if\s+__name__\s*==\s*['\"]__main__['\"]\s*:"
    if not re.search(pattern, code):
        return code
    # Find the __main__ line
    lines = code.split('\n')
    new_lines = []
    in_main = False
    main_indent = 0
    for line in lines:
        if re.match(pattern, line.strip()):
            in_main = True
            main_indent = len(line) - len(line.lstrip())
            # Add a comment instead
            new_lines.append(line[:main_indent] + "# === EXECUTION BLOCK ===")
            continue
        if in_main:
            if line.strip() == '':
                new_lines.append(line)
                continue
            current_indent = len(line) - len(line.lstrip())
            if current_indent <= main_indent:
                in_main = False
                new_lines.append(line)
                continue
            # Reduce indent by the __main__ indent level
            new_line = line[main_indent:] if len(line) > main_indent else line
            new_lines.append(new_line)
            continue
        new_lines.append(line)
    return '\n'.join(new_lines)

def fix_source_imports(code):
    """Comment out imports from Source package"""
    lines = code.split('\n')
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if (stripped.startswith('from Source.') or stripped.startswith('import Source.')) and not stripped.startswith('#'):
            new_lines.append('# ' + line)
            continue
        # Fix matplotlib.use('Agg')
        if "matplotlib.use('Agg')" in line or 'matplotlib.use("Agg")' in line:
            new_lines.append('# ' + line + '  # Colab: no need for non-interactive backend')
            continue
        new_lines.append(line)
    return '\n'.join(new_lines)

cells = []

# ================================================================
# 1. COVER - Opening narrative
# ================================================================
cells.append(md_cell("""<div style="text-align:center;padding:40px 20px;background:linear-gradient(135deg,#0D47A1,#1565C0);border-radius:15px;color:white;margin-bottom:20px">
<h1 style="color:white;font-size:2.2rem"> Master Data Management (MDM)</h1>
<h2 style="color:#FFD54F;font-size:1.6rem">Direktorat Jenderal Bea dan Cukai (DJBC)</h2>
<h3 style="color:#E3F2FD">Single Importer & Exporter View — Kelompok 5</h3>
<hr style="border:1px solid rgba(255,255,255,0.3);width:60%;margin:20px auto">
<p style="font-size:1rem;max-width:800px;margin:20px auto;line-height:1.6">
<b>Mini Project — Implementasi MDM untuk Data Importir & Eksportir Nasional</b><br>
Mengintegrasikan data dari <b>OSS (Online Single Submission)</b> sebagai sumber legalitas
dan <b>CEISA (Customs Excise Information System)</b> sebagai sumber operasional
menjadi <b>Golden Record</b> tunggal yang terpercaya.
</p>
<div style="display:flex;justify-content:center;gap:20px;flex-wrap:wrap;margin-top:20px">
<div style="background:rgba(255,255,255,0.15);padding:10px 20px;border-radius:10px"><b>Tahapan:</b> 7 Fase (0-6)</div>
<div style="background:rgba(255,255,255,0.15);padding:10px 20px;border-radius:10px"><b>Entitas:</b> 5.000 Perusahaan</div>
<div style="background:rgba(255,255,255,0.15);padding:10px 20px;border-radius:10px"><b>Tujuan:</b> Golden Record & DQ Scorecard</div>
</div>
</div>

## Daftar Isi

| Tahap | Judul | Deskripsi |
|:---:|---|---|
| **0** | Simulasi Data & Faker Engine | Pembangkitan dataset OSS & CEISA dengan anomali |
| **1** | Data Profiling | Analisis eksploratori, missing value, duplikasi, validitas |
| **2** | Data Cleansing & Standardisasi | Pembersihan nama, alamat, identifier, dedup CEISA |
| **3** | Duplicate Detection & Matching | Exact & fuzzy matching OSS vs CEISA |
| **4** | Golden Record & Survivorship | Pembentukan rekam emas tunggal per entitas |
| **5** | Data Quality Monitoring | Scorecard 5 dimensi DMBOK (Before vs After) |
| **6** | YData Profiling Dashboard | Profiling akhir Golden Record & insight bisnis |

---

### Narasi Pembuka

**Master Data Management (MDM)** adalah pendekatan strategis untuk mengelola data master perusahaan. Dalam konteks DJBC, data importir dan eksportir nasional tersebar di dua sistem utama: **OSS** (sistem perizinan berusaha) dan **CEISA** (sistem operasional kepabeanan).

**Permasalahan utama:**
1. Data tersebar di dua sistem yang tidak terintegrasi
2. Ketidakseragaman format data antar sistem
3. Duplikasi data intra-sistem maupun antar-sistem
4. Konflik data (status berbeda, data usang, dll.)

**Pipeline MDM yang diimplementasikan:** Simulasi data dengan anomali (Tahap 0) -> Profiling kualitas data (Tahap 1) -> Pembersihan dan standardisasi (Tahap 2) -> Pencocokan antar sumber (Tahap 3) -> Pembentukan Golden Record (Tahap 4) -> Monitoring kualitas (Tahap 5) -> Dashboard profiling akhir (Tahap 6).

> **Catatan:** Notebook ini dirancang untuk **Google Colab**. Semua library akan diinstall otomatis. Data akan disimpan di folder `/content/`."""))

# ================================================================
# 2. INSTALL LIBRARIES
# ================================================================
cells.append(md_cell("""## Setup Environment

### 1. Instalasi Library"""))

cells.append(code_cell("""# Install library yang dibutuhkan untuk Google Colab
import warnings
warnings.filterwarnings('ignore')

!pip install missingno faker ydata-profiling fuzzywuzzy python-Levenshtein jellyfish recordlinkage networkx -q

print('Semua library berhasil diinstall!')"""))

# ================================================================
# 3. IMPORT LIBRARIES
# ================================================================
cells.append(md_cell("""### 2. Import Semua Library"""))

cells.append(code_cell("""import pandas as pd
import numpy as np
import re, random, warnings, os
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Callable

warnings.filterwarnings('ignore')

from faker import Faker
import matplotlib.pyplot as plt
import seaborn as sns
import missingno as msno
from fuzzywuzzy import fuzz
import jellyfish
import recordlinkage
import networkx as nx
from ydata_profiling import ProfileReport

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', 50)
pd.set_option('display.float_format', '{:.2f}'.format)
pd.set_option('display.width', 140)

sns.set_theme(style='whitegrid', palette='Blues_d')
plt.rcParams['figure.figsize'] = (12, 5)

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)
Faker.seed(RANDOM_SEED)

print('Semua library berhasil diimport!')
print(f'Pandas: {pd.__version__}, NumPy: {np.__version__}')"""))

# ================================================================
# 4. SETUP DIRECTORIES
# ================================================================
cells.append(md_cell("""### 3. Setup Direktori Google Colab

Membuat struktur folder untuk menyimpan data dan laporan."""))

cells.append(code_cell("""# Setup direktori untuk Google Colab
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
print(f'  Laporan       : {REPORTS_DIR}/')"""))

# ================================================================
# TAHAP 0 - REFERENCE
# ================================================================
cells.append(md_cell("""# TAHAP 0: SIMULASI DATA & FAKER ENGINE

**Tujuan:** Membangkitkan dataset simulasi yang mencerminkan kompleksitas dunia nyata di DJBC, lengkap dengan anomali untuk menguji sistem MDM.

### Lab 0.1 — Data Referensi DJBC

Kode referensi standar DJBC: provinsi, KPPBC, enum values."""))

ref_code = read_file(os.path.join(SOURCE_DIR, 'step02_reference.py'))
ref_code = ref_code.replace("print(f'✅ Lab 0.1: Referensi DJBC Siap (Align dengan Data Dictionary)')", "print('Referensi DJBC siap')")
cells.append(code_cell(ref_code))

# ================================================================
# TAHAP 0 - GENERATORS
# ================================================================
cells.append(md_cell("""### Lab 0.2 — Generator Identifier DJBC

Fungsi untuk menghasilkan NIB, NPWP, API, NIPER, dan tanggal."""))

cells.append(code_cell(read_file(os.path.join(SOURCE_DIR, 'step03_generators.py'))))

# ================================================================
# TAHAP 0 - SIMULATION
# ================================================================
cells.append(md_cell("""### Lab 1 — DJBC Data Simulation Engine

Membangkitkan 5.000 perusahaan dengan anomali: NPWP kotor, typo nama, konflik status, logical conflict, duplicate entry, snapshot duplicate, stale data."""))

sim_code = read_file(os.path.join(SOURCE_DIR, 'step04_simulation.py'))
sim_code = fix_source_imports(sim_code)
sim_code = fix_paths(sim_code)
sim_code = remove_main_section(sim_code)
# Fix the simulation function call at end
if 'run_full_simulation()' in sim_code:
    # Make sure it's not inside the __main__ block anymore
    pass
cells.append(code_cell(sim_code))

# ================================================================
# TAHAP 1 - PROFILING FUNCTIONS
# ================================================================
cells.append(md_cell("""# TAHAP 1: DATA PROFILING

**Tujuan:** Eksplorasi dan pengukuran kualitas data baseline sebelum cleansing/MDM.

### Definisi Fungsi Profiling"""))

prof_code = read_file(os.path.join(SOURCE_DIR, 'step05_profiling.py'))
prof_code = fix_source_imports(prof_code)
prof_code = fix_paths(prof_code)
prof_code = remove_main_section(prof_code)
# Ensure NIB_PATTERN, NPWP_PATTERN are defined
if 'NIB_PATTERN' not in prof_code:
    prof_code = 'NIB_PATTERN = re.compile(r"^\\d{13}$")\nNPWP_PATTERN = re.compile(r"^\\d{2}\\.\\d{3}\\.\\d{3}\\.\\d{1}-\\d{3}\\.\\d{3}$")\nKODE_POS_PATTERN = re.compile(r"^\\d{5}$")\nDUMMY_NIB = "0" * 13\n\n' + prof_code
# Add YDATA_CORRELATIONS if missing
if 'YDATA_CORRELATIONS' not in prof_code:
    prof_code += '\n\nYDATA_CORRELATIONS = {\n    "auto": {"calculate": False},\n    "pearson": {"calculate": True},\n    "spearman": {"calculate": False},\n    "kendall": {"calculate": False},\n    "phi_k": {"calculate": False},\n    "cramers": {"calculate": False},\n}\n'
cells.append(code_cell(prof_code))

# ================================================================
# TAHAP 1 - EXECUTION
# ================================================================
cells.append(md_cell("""### Eksekusi Profiling — OSS"""))

cells.append(code_cell("""df_oss = pd.read_csv(f'{DATA_RAW}/oss_nib_data.csv', dtype={'NIB': str, 'NPWP_PERSEROAN': str})
print(f'Dataset OSS: {len(df_oss):,} baris')

dataset_overview(df_oss, 'OSS')
descriptive_stats(df_oss, 'OSS')
missing_oss = missing_value_analysis(df_oss, 'OSS')
dup_oss = duplicate_analysis(df_oss, 'OSS', 'NAMA_PERSEROAN')
fmt_oss = format_validation(df_oss, 'OSS')"""))

cells.append(md_cell("""### Eksekusi Profiling — CEISA"""))

cells.append(code_cell("""df_ceisa = pd.read_csv(f'{DATA_RAW}/ceisa_data.csv', dtype={'NIB': str, 'NPWP': str})
print(f'Dataset CEISA: {len(df_ceisa):,} baris')

dataset_overview(df_ceisa, 'CEISA')
descriptive_stats(df_ceisa, 'CEISA')
missing_ceisa = missing_value_analysis(df_ceisa, 'CEISA')
dup_ceisa = duplicate_analysis(df_ceisa, 'CEISA', 'NAMA_PERUSAHAAN')
fmt_ceisa = format_validation(df_ceisa, 'CEISA')"""))

cells.append(md_cell("""### Baseline Data Quality Score (4 Dimensi DMBOK)"""))

cells.append(code_cell("""oss_metrics = calculate_dq_metrics(df_oss, 'OSS')
ceisa_metrics = calculate_dq_metrics(df_ceisa, 'CEISA')

dq_compare = pd.DataFrame({
    'Dimensi': list(oss_metrics.keys()),
    'OSS (%)': [f'{oss_metrics[k]:.2f}%' for k in oss_metrics],
    'CEISA (%)': [f'{ceisa_metrics[k]:.2f}%' for k in ceisa_metrics],
})
display(dq_compare)

avg_oss = sum(oss_metrics.values()) / len(oss_metrics)
avg_ceisa = sum(ceisa_metrics.values()) / len(ceisa_metrics)
print(f'\\nOverall DQ Score: OSS={avg_oss:.2f}% | CEISA={avg_ceisa:.2f}%')

# Radar chart
fig, ax = plt.subplots(figsize=(8,8), subplot_kw=dict(polar=True))
dims = list(oss_metrics.keys())
angles = np.linspace(0, 2*np.pi, len(dims), endpoint=False).tolist() + [0]
ov = list(oss_metrics.values()) + [list(oss_metrics.values())[0]]
cv = list(ceisa_metrics.values()) + [list(ceisa_metrics.values())[0]]
ax.plot(angles, ov, 'o-', lw=2, color='#1565C0', label='OSS')
ax.fill(angles, ov, alpha=0.1, color='#1565C0')
ax.plot(angles, cv, 'o-', lw=2, color='#F44336', label='CEISA')
ax.fill(angles, cv, alpha=0.1, color='#F44336')
ax.set_xticks(angles[:-1]); ax.set_xticklabels(dims, fontsize=11, fontweight='bold')
ax.set_ylim(0, 100); ax.set_title('Baseline DQ Score', fontsize=14, fontweight='bold', pad=20)
ax.legend(loc='upper right', bbox_to_anchor=(1.2, 1.1))
plt.tight_layout()
plt.savefig(f'{REPORTS_DIR}/dq_baseline.png', dpi=150, bbox_inches='tight')
plt.show()"""))

cells.append(md_cell("""### Laporan YData Profiling"""))

cells.append(code_cell("""print('Membuat YData Profiling untuk OSS...')
ProfileReport(
    df_oss, title='OSS (Before MDM)', explorative=True,
    correlations=YDATA_CORRELATIONS, interactions={'continuous': False}
).to_file(f'{REPORTS_DIR}/profiling_before_oss.html')
print(f'OK: {REPORTS_DIR}/profiling_before_oss.html')

print('Membuat YData Profiling untuk CEISA...')
ProfileReport(
    df_ceisa, title='CEISA (Before MDM)', explorative=True,
    correlations=YDATA_CORRELATIONS, interactions={'continuous': False}
).to_file(f'{REPORTS_DIR}/profiling_before_ceisa.html')
print(f'OK: {REPORTS_DIR}/profiling_before_ceisa.html')

print('Tahap 1 selesai!')"""))

# ================================================================
# TAHAP 2 - CLEANSING FUNCTIONS
# ================================================================
cells.append(md_cell("""# TAHAP 2: DATA CLEANSING & STANDARDIZATION

**Tujuan:** Membersihkan dan menstandarisasi data OSS & CEISA agar konsisten.

### Definisi Fungsi Cleansing"""))

cleansing_code = read_file(os.path.join(SOURCE_DIR, 'step06_cleansing.py'))
cleansing_code = fix_source_imports(cleansing_code)
cleansing_code = fix_paths(cleansing_code)
cleansing_code = remove_main_section(cleansing_code)
# Ensure DUMMY_NIB is defined
if 'DUMMY_NIB' not in cleansing_code:
    cleansing_code = 'DUMMY_NIB = "0" * 13\n\n' + cleansing_code
cells.append(code_cell(cleansing_code))

# ================================================================
# TAHAP 2 - EXECUTION
# ================================================================
cells.append(md_cell("""### Eksekusi Cleansing OSS & CEISA

Menjalankan pipeline cleansing pada kedua dataset."""))

cells.append(code_cell("""print('CLEANSING OSS...')
df_oss_raw = pd.read_csv(f'{DATA_RAW}/oss_nib_data.csv', dtype={'NIB': str, 'NPWP_PERSEROAN': str})
df_ceisa_raw = pd.read_csv(f'{DATA_RAW}/ceisa_data.csv', dtype={'NIB': str, 'NPWP': str})

audit = AuditTrail()
metrics_oss_before = calculate_dq_metrics(df_oss_raw, dataset_name='OSS')
df_oss_clean = clean_oss(df_oss_raw, audit)
metrics_oss_after = calculate_dq_metrics(df_oss_clean, dataset_name='OSS')
print(f'Hasil: {len(df_oss_raw):,} -> {len(df_oss_clean):,} baris')
quality_gate(df_oss_clean, 'OSS', MAND_COLS_OSS)
print_dq_comparison(metrics_oss_before, metrics_oss_after, 'OSS')

print('\\nCLEANSING CEISA...')
metrics_ceisa_before = calculate_dq_metrics(df_ceisa_raw, dataset_name='CEISA')
df_ceisa_clean = clean_ceisa(df_ceisa_raw, audit)
metrics_ceisa_after = calculate_dq_metrics(df_ceisa_clean, dataset_name='CEISA')
print(f'Hasil: {len(df_ceisa_raw):,} -> {len(df_ceisa_clean):,} baris')
quality_gate(df_ceisa_clean, 'CEISA', MAND_COLS_CEISA)
print_dq_comparison(metrics_ceisa_before, metrics_ceisa_after, 'CEISA')"""))

cells.append(md_cell("""### Export Data Bersih & Audit Trail"""))

cells.append(code_cell("""# Export cleaned datasets
df_oss_clean.to_csv(f'{DATA_PROCESSED}/oss_cleaned.csv', index=False)
df_ceisa_clean.to_csv(f'{DATA_PROCESSED}/ceisa_cleaned.csv', index=False)

# Union OSS + CEISA
df_clean = pd.concat([
    df_oss_clean.assign(SOURCE='OSS'),
    df_ceisa_clean.assign(SOURCE='CEISA')
], ignore_index=True, sort=False)
df_clean.to_csv(f'{DATA_PROCESSED}/dataset_clean.csv', index=False)

# Audit trail
audit.to_dataframe().to_csv(f'{REPORTS_DIR}/audit_trail.csv', index=False)

print('File exported:')
print(f'  - {DATA_PROCESSED}/oss_cleaned.csv ({len(df_oss_clean):,})')
print(f'  - {DATA_PROCESSED}/ceisa_cleaned.csv ({len(df_ceisa_clean):,})')
print(f'  - {DATA_PROCESSED}/dataset_clean.csv ({len(df_clean):,})')
print(f'  - {REPORTS_DIR}/audit_trail.csv')
print('Tahap 2 selesai!')"""))

# ================================================================
# TAHAP 3 - MATCHING FUNCTIONS
# ================================================================
cells.append(md_cell("""# TAHAP 3: DUPLICATE DETECTION & MATCHING

**Tujuan:** Mencocokkan data OSS dan CEISA untuk mengidentifikasi entitas yang sama.

Prioritas: 1) Exact NIB, 2) Exact NPWP, 3) Fuzzy nama+alamat.

### Definisi Fungsi Matching"""))

match_code = read_file(os.path.join(SOURCE_DIR, 'step07_matching.py'))
match_code = fix_source_imports(match_code)
match_code = fix_paths(match_code)
match_code = remove_main_section(match_code)
# Ensure constants defined
for const in ['UPPER_THRESHOLD', 'LOWER_THRESHOLD', 'DUMMY_NIB']:
    if const not in match_code:
        match_code = f'{const} = 0.85  # Default\n' + match_code if const == 'UPPER_THRESHOLD' else match_code
cells.append(code_cell(match_code))

# ================================================================
# TAHAP 3 - EXECUTION
# ================================================================
cells.append(md_cell("""### Eksekusi Matching Pipeline"""))

cells.append(code_cell("""print('TAHAP 3: DUPLICATE DETECTION & MATCHING')
print('=' * 60)

# Load data
df_oss = pd.read_csv(f'{DATA_PROCESSED}/oss_cleaned.csv', dtype={'NIB': str, 'NPWP_PERSEROAN': str})
df_ceisa = pd.read_csv(f'{DATA_PROCESSED}/ceisa_cleaned.csv', dtype={'NIB': str, 'NPWP': str})
print(f'OSS={len(df_oss):,} baris, CEISA={len(df_ceisa):,} baris')

# Prepare matching keys
df_oss, df_ceisa = prepare_matching_keys(df_oss, df_ceisa)
print('Matching keys siap')

# Exact match NIB (Priority 1)
exact_nib_pairs = exact_match_nib(df_oss, df_ceisa)
matched_oss_nib = set(exact_nib_pairs['NIB_OSS'])
matched_ceisa_id = set(exact_nib_pairs['ID_PERUSAHAAN_CEISA'])
print(f'Exact NIB: {len(exact_nib_pairs):,} pairs')

remaining_oss = df_oss[~df_oss['NIB'].isin(matched_oss_nib)].copy()
remaining_ceisa = df_ceisa[~df_ceisa['ID_PERUSAHAAN'].isin(matched_ceisa_id)].copy()

# Exact match NPWP (Priority 2)
exact_npwp_pairs = exact_match_npwp(remaining_oss, remaining_ceisa)
matched_oss_npwp = set(exact_npwp_pairs['NIB_OSS'])
matched_ceisa_npwp = set(exact_npwp_pairs['ID_PERUSAHAAN_CEISA'])
print(f'Exact NPWP: {len(exact_npwp_pairs):,} pairs')

remaining_oss = remaining_oss[~remaining_oss['NIB'].isin(matched_oss_npwp)].copy()
remaining_ceisa = remaining_ceisa[~remaining_ceisa['ID_PERUSAHAAN'].isin(matched_ceisa_npwp)].copy()
print(f'Sisa belum match: OSS={len(remaining_oss):,}, CEISA={len(remaining_ceisa):,}')

# Fuzzy matching (Priority 3)
print('Fuzzy matching (blocking per region_key)...')
df_fuzzy = fuzzy_match(remaining_oss, remaining_ceisa)
print(f'Kandidat fuzzy: {len(df_fuzzy):,}')

# Classify
if not df_fuzzy.empty:
    df_fuzzy['match_type'] = df_fuzzy['composite_score'].apply(classify_pair)
    df_fuzzy = df_fuzzy.sort_values('composite_score', ascending=False).reset_index(drop=True)

# Visualisasi distribusi
print('\\nVisualisasi distribusi composite score...')
plot_score_distribution(df_fuzzy, output_path=f'{REPORTS_DIR}/composite_score_distribution.png')
threshold_analysis(df_fuzzy)
spot_check(df_fuzzy)

# Duplicate clustering
print('\\nDuplicate clustering internal...')
oss_clusters = cluster_oss_duplicates(df_oss)
ceisa_clusters = cluster_ceisa_similar(df_ceisa)
df_clusters = pd.concat([oss_clusters, ceisa_clusters], ignore_index=True)
print(f'OSS clusters: {oss_clusters["cluster_id"].nunique() if not oss_clusters.empty else 0}')
print(f'CEISA clusters: {ceisa_clusters["cluster_id"].nunique() if not ceisa_clusters.empty else 0}')

# Export
fuzzy_export = pd.DataFrame(columns=['NIB_OSS', 'ID_PERUSAHAAN_CEISA', 'NIB_CEISA', 'match_type', 'similarity_score'])
if not df_fuzzy.empty:
    fz = df_fuzzy[df_fuzzy['match_type'].isin(['FUZZY_MATCH', 'FUZZY_REVIEW'])][
        ['NIB_OSS', 'ID_PERUSAHAAN_CEISA', 'NIB_CEISA', 'match_type', 'composite_score']
    ].rename(columns={'composite_score': 'similarity_score'})
    fuzzy_export = fz

candidate_pairs = pd.concat(
    [exact_nib_pairs, exact_npwp_pairs, fuzzy_export], ignore_index=True
)
candidate_pairs.to_csv(f'{REPORTS_DIR}/candidate_pairs.csv', index=False)
df_clusters.to_csv(f'{REPORTS_DIR}/duplicate_cluster.csv', index=False)

print(f'\\nCandidate pairs: {len(candidate_pairs):,}')
print(f'  EXACT_NIB: {len(exact_nib_pairs):,}')
print(f'  EXACT_NPWP: {len(exact_npwp_pairs):,}')
print(f'  FUZZY: {len(fuzzy_export):,}')

matched_oss_all = matched_oss_nib | matched_oss_npwp | set(fuzzy_export['NIB_OSS'].dropna())
matched_ceisa_all = matched_ceisa_id | matched_ceisa_npwp | set(fuzzy_export['ID_PERUSAHAAN_CEISA'].dropna())
print(f'Orphan OSS: {(~df_oss["NIB"].isin(matched_oss_all)).sum():,}')
print(f'Orphan CEISA: {(~df_ceisa["ID_PERUSAHAAN"].isin(matched_ceisa_all)).sum():,}')
print('Tahap 3 selesai!')"""))

# ================================================================
# TAHAP 4 - GOLDEN RECORD
# ================================================================
cells.append(md_cell("""# TAHAP 4: GOLDEN RECORD & SURVIVORSHIP

**Tujuan:** Membentuk satu Golden Record per entitas dari gabungan OSS dan CEISA.

Aturan survivorship: OSS menang untuk legalitas (System of Record), CEISA menang untuk operasional.

### Definisi Fungsi Golden Record"""))

golden_code = read_file(os.path.join(SOURCE_DIR, 'step08_golden_record.py'))
golden_code = fix_source_imports(golden_code)
golden_code = fix_paths(golden_code)
golden_code = remove_main_section(golden_code)
cells.append(code_cell(golden_code))

# ================================================================
# TAHAP 4 - EXECUTION
# ================================================================
cells.append(md_cell("""### Eksekusi Golden Record Pipeline"""))

cells.append(code_cell("""print('TAHAP 4: GOLDEN RECORD & SURVIVORSHIP')
print('=' * 60)

# Load data
df_oss = pd.read_csv(f'{DATA_PROCESSED}/oss_cleaned.csv', dtype={'NIB': str, 'NPWP_PERSEROAN': str})
df_ceisa = pd.read_csv(f'{DATA_PROCESSED}/ceisa_cleaned.csv', dtype={'NIB': str, 'NPWP': str})
candidate_pairs = pd.read_csv(f'{REPORTS_DIR}/candidate_pairs.csv', dtype={'NIB_OSS': str, 'NIB_CEISA': str})
df_clusters = pd.read_csv(f'{REPORTS_DIR}/duplicate_cluster.csv')
print(f'OSS={len(df_oss):,}, CEISA={len(df_ceisa):,}, Pairs={len(candidate_pairs):,}')

# Dedup OSS duplicate entry
n_before = len(df_oss)
drop_ids = []
if not df_clusters.empty:
    for _, grp in df_clusters[df_clusters['source'] == 'OSS'].groupby('cluster_id'):
        ids = sorted(grp['record_id'].astype(int).tolist())
        drop_ids.extend(ids[1:])
df_oss = df_oss.drop(index=drop_ids).reset_index(drop=True)
df_oss['_ROW_ID'] = df_oss.index
print(f'Dedup OSS: {n_before:,} -> {len(df_oss):,} baris ({len(drop_ids)} dibuang)')

print(f'\\nFIELD_RULES: {len(FIELD_RULES)} field di-mapping')
print('OSS=System of Record (legalitas), CEISA menang untuk field operasional')

# Process matched pairs
print('\\nProses matched pairs...')
pairs = candidate_pairs.drop_duplicates(subset='NIB_OSS', keep='first')
oss_idx = df_oss.set_index('NIB', drop=False)
ceisa_idx = df_ceisa.set_index('ID_PERUSAHAAN', drop=False)
ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

golden_rows, prov_rows, conflict_rows = [], [], []
matched_oss_ids, matched_ceisa_ids = set(), set()

for _, pair in pairs.iterrows():
    ceisa_row = ceisa_idx.loc[pair['ID_PERUSAHAAN_CEISA']]
    cand_oss = oss_idx.loc[[pair['NIB_OSS']]]
    if len(cand_oss) == 1:
        oss_row = cand_oss.iloc[0]
    else:
        scores = cand_oss['NAMA_PERSEROAN'].apply(
            lambda n: fuzz.token_set_ratio(normalize_for_matching(n),
                                           normalize_for_matching(ceisa_row['NAMA_PERUSAHAAN']))
        )
        oss_row = cand_oss.iloc[scores.values.argmax()]
    matched_oss_ids.add(oss_row['_ROW_ID'])
    matched_ceisa_ids.add(ceisa_row['_ROW_ID'])
    golden, prov = create_golden_record(oss_row, ceisa_row, FIELD_RULES)
    ios = str(oss_row['STATUS_NIB']).strip() != str(ceisa_row['STATUS_NIB']).strip()
    lc = is_logical_conflict_niper(oss_row, ceisa_row)
    fc = detect_field_conflicts(oss_row, ceisa_row)
    nc = len(fc) + (1 if lc else 0)
    golden.update({
        'SOURCE': 'MATCHED', 'MATCH_TYPE': pair['match_type'], 'SOURCE_COUNT': 2,
        'N_CONFLICTS': nc, 'IS_OUT_OF_SYNC': ios,
        'IS_STALE': bool(oss_row['IS_STALE']), 'HIGH_SYNC_LAG': bool(ceisa_row['HIGH_SYNC_LAG']),
        'IS_LOGICAL_CONFLICT_NIPER': lc, 'CREATED_AT': ts,
    })
    golden_rows.append(golden)
    for f, s in prov.items():
        prov_rows.append({'NIB': golden['NIB'], 'field': f, 'source': s})
    for f, ov, cv in fc:
        conflict_rows.append({'NIB': golden['NIB'], 'field': f, 'oss_value': ov, 'ceisa_value': cv, 'winner': 'OSS'})
    if lc:
        conflict_rows.append({'NIB': golden['NIB'], 'field': 'FLAG_EKSPOR_vs_NIPER',
                              'oss_value': oss_row['FLAG_EKSPOR'], 'ceisa_value': ceisa_row['NIPER'],
                              'winner': 'OSS (FLAG_EKSPOR)'})

print(f'{len(golden_rows):,} golden dari matched pairs')

# Orphan records
print('\\nProses orphan records...')
for _, r in df_oss[~df_oss['_ROW_ID'].isin(matched_oss_ids)].iterrows():
    g, pv = create_golden_record(r, None, FIELD_RULES)
    g.update({'SOURCE': 'OSS_ONLY', 'MATCH_TYPE': 'N/A', 'SOURCE_COUNT': 1, 'N_CONFLICTS': 0,
              'IS_OUT_OF_SYNC': False, 'IS_STALE': bool(r['IS_STALE']),
              'HIGH_SYNC_LAG': None, 'IS_LOGICAL_CONFLICT_NIPER': False, 'CREATED_AT': ts})
    golden_rows.append(g)
    for f, s in pv.items(): prov_rows.append({'NIB': g['NIB'], 'field': f, 'source': s})

for _, r in df_ceisa[~df_ceisa['_ROW_ID'].isin(matched_ceisa_ids)].iterrows():
    g, pv = create_golden_record(None, r, FIELD_RULES)
    g.update({'SOURCE': 'CEISA_ONLY', 'MATCH_TYPE': 'N/A', 'SOURCE_COUNT': 1, 'N_CONFLICTS': 0,
              'IS_OUT_OF_SYNC': False, 'IS_STALE': None,
              'HIGH_SYNC_LAG': bool(r['HIGH_SYNC_LAG']),
              'IS_LOGICAL_CONFLICT_NIPER': False, 'CREATED_AT': ts})
    golden_rows.append(g)
    for f, s in pv.items(): prov_rows.append({'NIB': g['NIB'], 'field': f, 'source': s})

n_oss_only = sum(1 for r in golden_rows if r['SOURCE'] == 'OSS_ONLY')
n_ceisa_only = sum(1 for r in golden_rows if r['SOURCE'] == 'CEISA_ONLY')
print(f'OSS_ONLY: {n_oss_only:,}, CEISA_ONLY: {n_ceisa_only:,}')

# Build dataframe
df_golden = pd.DataFrame(golden_rows)
df_golden.insert(0, 'GR_ID', [f'GR{i:06d}' for i in range(1, len(df_golden) + 1)])
df_golden = df_golden[GOLDEN_COLUMNS]
df_provenance = pd.DataFrame(prov_rows)
df_conflicts = pd.DataFrame(conflict_rows, columns=['NIB', 'field', 'oss_value', 'ceisa_value', 'winner'])

print(f'\\nTotal Golden Record: {len(df_golden):,}')
print(f'  MATCHED: {(df_golden["SOURCE"]=="MATCHED").sum():,}')
print(f'  OSS_ONLY: {n_oss_only:,}')
print(f'  CEISA_ONLY: {n_ceisa_only:,}')"""))

cells.append(md_cell("""### Analisis Konflik, Provenance & Validasi"""))

cells.append(code_cell("""# Analisis konflik
n_matched = (df_golden['SOURCE'] == 'MATCHED').sum()
print(f'Analisis Konflik ({n_matched:,} matched):')
print(f'  Pairs dengan konflik: {(df_golden.loc[df_golden["SOURCE"]=="MATCHED", "N_CONFLICTS"] > 0).sum():,}')
if not df_conflicts.empty:
    for f, ct in df_conflicts['field'].value_counts().head(10).items():
        print(f'  {f:<25}: {ct:>5,} ({ct/n_matched*100:.1f}%)')

# Provenance
if not df_provenance.empty:
    prov_sum = df_provenance.groupby(['field', 'source']).size().unstack(fill_value=0)
    for s in ['OSS', 'CEISA', 'N/A']:
        if s not in prov_sum.columns: prov_sum[s] = 0
    prov_sum = prov_sum[['OSS', 'CEISA', 'N/A']]
    print('\\nProvenance per field:')
    display(prov_sum)
    overall = df_provenance['source'].value_counts(normalize=True) * 100
    print('\\nKontribusi per sumber:')
    for s, v in overall.items():
        print(f'  {s:<6}: {v:.1f}%')

# Validation
print('\\nQuality Validation:')
n_ni = (~df_golden['NIB'].astype(str).str.match(NIB_PATTERN)).sum()
n_nv = (~df_golden['NPWP'].astype(str).str.match(NPWP_PATTERN)).sum()
n_si = (~df_golden['STATUS_NIB'].isin(STATUS_NIB_POOL)).sum()
is_dummy = df_golden['NIB'].astype(str) == DUMMY_NIB
n_dup = df_golden.loc[~is_dummy, 'NIB'].duplicated().sum()
print(f'  NIB valid: {"PASS" if n_ni==0 else "INFO"} ({n_ni:,} invalid)')
print(f'  NPWP valid: {"PASS" if n_nv==0 else "INFO"} ({n_nv:,} invalid)')
print(f'  STATUS_NIB: {"PASS" if n_si==0 else "INFO"} ({n_si:,} invalid)')
print(f'  NIB unik: {"PASS" if n_dup==0 else "INFO"} ({n_dup:,} dup)')
if is_dummy.sum() > 0:
    print(f'  {is_dummy.sum():,} NIB dummy (dipertahankan)')

# Export
df_golden.to_csv(f'{DATA_GOLDEN}/golden_record.csv', index=False)
df_provenance.to_csv(f'{REPORTS_DIR}/provenance_log.csv', index=False)
df_conflicts.to_csv(f'{REPORTS_DIR}/conflict_log.csv', index=False)

print(f'\\nGolden Record: {DATA_GOLDEN}/golden_record.csv ({len(df_golden):,})')
print(f'Provenance: {REPORTS_DIR}/provenance_log.csv')
print(f'Conflict: {REPORTS_DIR}/conflict_log.csv')
print('Tahap 4 selesai!')"""))

# ================================================================
# TAHAP 5 - DQ MONITORING
# ================================================================
cells.append(md_cell("""# TAHAP 5: DATA QUALITY MONITORING

**Tujuan:** Mengukur dan membandingkan kualitas data Before vs After MDM menggunakan 5 dimensi DMBOK.

### Definisi Quality Rules Engine"""))

dq_code = read_file(os.path.join(SOURCE_DIR, 'step09_quality_monitoring.py'))
dq_code = fix_source_imports(dq_code)
dq_code = fix_paths(dq_code)
dq_code = remove_main_section(dq_code)
cells.append(code_cell(dq_code))

# ================================================================
# TAHAP 5 - EXECUTION
# ================================================================
cells.append(md_cell("""### Eksekusi Quality Rules & Scorecard"""))

cells.append(code_cell("""print('TAHAP 5: DATA QUALITY MONITORING')
print('=' * 60)

# Load data
df_oss = pd.read_csv(f'{DATA_PROCESSED}/oss_cleaned.csv', dtype={'NIB': str, 'NPWP_PERSEROAN': str})
df_ceisa = pd.read_csv(f'{DATA_PROCESSED}/ceisa_cleaned.csv', dtype={'NIB': str, 'NPWP': str})
df_golden = pd.read_csv(f'{DATA_GOLDEN}/golden_record.csv', dtype={'NIB': str, 'NPWP': str})
print(f'OSS={len(df_oss):,}, CEISA={len(df_ceisa):,}, Golden={len(df_golden):,}')

# Eksekusi rules
print('\\nMenjalankan quality rules...')
results_oss = run_rules(df_oss, OSS_RULES, 'OSS')
results_ceisa = run_rules(df_ceisa, CEISA_RULES, 'CEISA')
results_golden = run_rules(df_golden, GOLDEN_RULES, 'GOLDEN')
df_results = pd.DataFrame([r.__dict__ for r in results_oss + results_ceisa + results_golden])

# Display results
def print_rules(rs, label):
    print(f'\\n--- {label} ---')
    for r in rs:
        s = chr(9989) if r.pass_rate == 100 else (chr(9888) + chr(65039) if r.pass_rate >= 95 else chr(10060))
        print(f'  {s} {r.rule_id:<15} {r.dimension:<13} {r.pass_rate:>6.2f}% ({r.n_pass:,}/{r.total:,})')

print_rules(results_oss, 'OSS (Before)')
print_rules(results_ceisa, 'CEISA (Before)')
print_rules(results_golden, 'Golden Record (After)')

# Scorecard
print('\\nScorecard perbandingan:')
df_scorecard = build_scorecard(df_results)
display(df_scorecard.style.format('{:.2f}').background_gradient(cmap='RdYlGn'))

# Export
df_scorecard.to_csv(f'{REPORTS_DIR}/dq_scorecard.csv')
df_results.to_csv(f'{REPORTS_DIR}/dq_rule_results.csv', index=False)
print(f'\\nScorecard: {REPORTS_DIR}/dq_scorecard.csv')

ov = df_scorecard.loc['Overall']
print(f'\\nRINGKASAN OVERALL DQ SCORE')
print(f'OSS (Before):   {ov.get("OSS", 0):.2f}/100')
print(f'CEISA (Before): {ov.get("CEISA", 0):.2f}/100')
print(f'Golden (After): {ov.get("GOLDEN", 0):.2f}/100')
if 'OSS' in ov and 'GOLDEN' in ov:
    print(f'Delta vs OSS:   {ov["GOLDEN"] - ov["OSS"]:+.2f}')
if 'CEISA' in ov and 'GOLDEN' in ov:
    print(f'Delta vs CEISA: {ov["GOLDEN"] - ov["CEISA"]:+.2f}')
print('Tahap 5 selesai!')"""))

# ================================================================
# TAHAP 6 - DASHBOARD
# ================================================================
cells.append(md_cell("""# TAHAP 6: YDATA PROFILING DASHBOARD

**Tujuan:** Profiling ulang Golden Record, perbandingan Before vs After, insight bisnis & rekomendasi.

### Profiling Golden Record"""))

dashboard_code = read_file(os.path.join(SOURCE_DIR, 'step10_profiling_dashboard.py'))
dashboard_code = fix_source_imports(dashboard_code)
dashboard_code = fix_paths(dashboard_code)
dashboard_code = remove_main_section(dashboard_code)
cells.append(code_cell(dashboard_code))

# ================================================================
# TAHAP 6 - EXECUTION
# ================================================================
cells.append(md_cell("""### Perbandingan Before vs After"""))

cells.append(code_cell("""print('TAHAP 6: PERBANDINGAN BEFORE vs AFTER')
print('=' * 65)

# Load data
df_oss_orig = pd.read_csv(f'{DATA_RAW}/oss_nib_data.csv')
df_ceisa_orig = pd.read_csv(f'{DATA_RAW}/ceisa_data.csv')
df_golden = pd.read_csv(f'{DATA_GOLDEN}/golden_record.csv', dtype={'NIB': str, 'NPWP': str})

n_before = len(df_oss_orig) + len(df_ceisa_orig)
n_golden = len(df_golden)

print(f'\\n[Jumlah Record]')
print(f'  Before: {n_before:,} -> After: {n_golden:,} (pengurangan {n_before-n_golden:,} / {(1-n_golden/n_before)*100:.1f}%)')

# Format validity
def fmt_val(df, nib_c, npwp_c, kp_c):
    nib_v = df[nib_c].astype(str).str.match(NIB_PATTERN).mean()*100
    npwp_v = df[npwp_c].astype(str).str.match(NPWP_PATTERN).mean()*100
    kp_s = _to_digit_str(df[kp_c]).dropna()
    kp_v = kp_s.str.match(KODE_POS_PATTERN).mean()*100 if len(kp_s) else 0
    return nib_v, npwp_v, kp_v

no, no2, kpo = fmt_val(df_oss_orig, 'NIB', 'NPWP_PERSEROAN', 'KODE_POS_PERSEROAN')
nc, nc2, kpc = fmt_val(df_ceisa_orig, 'NIB', 'NPWP', 'KODE_POS')
ng, ng2, kpg = fmt_val(df_golden, 'NIB', 'NPWP', 'KODE_POS')

print(f'\\n[Format Validity]')
print(f'  {"Field":<22} {"OSS":>10} {"CEISA":>10} {"Golden":>10}')
print(f'  {"NIB":<22} {no:>9.2f}% {nc:>9.2f}% {ng:>9.2f}%')
print(f'  {"NPWP":<22} {no2:>9.2f}% {nc2:>9.2f}% {ng2:>9.2f}%')
print(f'  {"KODE_POS":<22} {kpo:>9.2f}% {kpc:>9.2f}% {kpg:>9.2f}%')

do = df_oss_orig['NIB'].duplicated().sum()
dc = df_ceisa_orig['NIB'].duplicated().sum()
dg = df_golden[df_golden['NIB'].astype(str)!=DUMMY_NIB]['NIB'].duplicated().sum()
print(f'\\n[Duplikasi NIB]')
print(f'  OSS: {do:,} ({do/len(df_oss_orig)*100:.2f}%)')
print(f'  CEISA: {dc:,} ({dc/len(df_ceisa_orig)*100:.2f}%)')
print(f'  Golden: {dg:,} ({dg/len(df_golden)*100:.2f}%)')

# Visualisasi
fig, axes = plt.subplots(1, 3, figsize=(16, 5))
fig.suptitle('Perbandingan Kualitas: Before vs After MDM', fontsize=14, fontweight='bold')

miss_o = df_oss_orig[['NIB','NPWP_PERSEROAN','NAMA_PERSEROAN','STATUS_NIB']].isnull().mean().mean()*100
miss_c = df_ceisa_orig[['NIB','NPWP','NAMA_PERUSAHAAN','STATUS_NIB']].isnull().mean().mean()*100
miss_g = 0
for cols in [['NIB','NPWP','NAMA','STATUS_NIB']]:
    if all(c in df_golden.columns for c in cols):
        miss_g = df_golden[cols].isnull().mean().mean()*100

axes[0].bar(['OSS','CEISA','Golden'],[miss_o, miss_c, miss_g], color=['#1565C0','#F44336','#2E7D32'])
axes[0].set_title('Missing Value % (Field Wajib)')
for i, v in enumerate([miss_o, miss_c, miss_g]):
    axes[0].text(i, v+0.3, f'{v:.2f}%', ha='center', fontweight='bold')

axes[1].bar(['OSS','CEISA','Golden'],[no, nc, ng], color=['#1565C0','#F44336','#2E7D32'])
axes[1].set_title('Validitas NIB (%)')
axes[1].set_ylim(0, 105)
for i, v in enumerate([no, nc, ng]):
    axes[1].text(i, v+1, f'{v:.2f}%', ha='center', fontweight='bold')

axes[2].bar(['OSS','CEISA','Golden'],[do/len(df_oss_orig)*100, dc/len(df_ceisa_orig)*100, dg/len(df_golden)*100],
            color=['#1565C0','#F44336','#2E7D32'])
axes[2].set_title('Duplikasi NIB (%)')
for i, v in enumerate([do/len(df_oss_orig)*100, dc/len(df_ceisa_orig)*100, dg/len(df_golden)*100]):
    axes[2].text(i, v+0.3, f'{v:.2f}%', ha='center', fontweight='bold')

plt.tight_layout()
plt.savefig(f'{REPORTS_DIR}/dq_comparison.png', dpi=150, bbox_inches='tight')
plt.show()"""))

cells.append(md_cell("""### Laporan YData Profiling Golden Record"""))

cells.append(code_cell("""print('Membuat YData Profiling untuk Golden Record...')
profile = ProfileReport(
    df_golden, title='Golden Record (After MDM)', explorative=True,
    correlations=YDATA_CORRELATIONS, interactions={'continuous': False}
)
profile.to_file(f'{REPORTS_DIR}/profiling_after.html')
print(f'OK: {REPORTS_DIR}/profiling_after.html')"""))

cells.append(md_cell("""### Insight Bisnis & Rekomendasi Data Governance"""))

cells.append(code_cell("""nd = (df_golden['NIB'].astype(str) == DUMMY_NIB).sum()
nos = int(df_golden['IS_OUT_OF_SYNC'].sum()) if 'IS_OUT_OF_SYNC' in df_golden else 0
nlc = int(df_golden['IS_LOGICAL_CONFLICT_NIPER'].sum()) if 'IS_LOGICAL_CONFLICT_NIPER' in df_golden else 0
nl = int(df_golden['HIGH_SYNC_LAG'].apply(lambda x: bool(x) if pd.notna(x) else False).sum()) if 'HIGH_SYNC_LAG' in df_golden else 0

print('=' * 65)
print('  INSIGHT BISNIS & REKOMENDASI')
print('=' * 65)
print(f'''
CAPAIAN PIPELINE MDM:
1. Konsolidasi {n_before:,} -> {n_golden:,} Golden Record ({(1-n_golden/n_before)*100:.1f}% reduksi)
2. Duplikasi NIB: {do/len(df_oss_orig)*100:.1f}% (OSS) / {dc/len(df_ceisa_orig)*100:.1f}% (CEISA) -> {dg/len(df_golden)*100:.1f}% (Golden)
3. Validitas NIB: {no:.1f}% (OSS) / {nc:.1f}% (CEISA) -> {ng:.1f}% (Golden)

RISIKO YANG PERLU DITINDAKLANJUTI:
1. {nd:,} record NIB dummy/tidak valid - verifikasi ke OSS
2. {nos:,} record Sync Conflict (STATUS_NIB beda OSS vs CEISA)
3. {nlc:,} record Logical Conflict (FLAG_EKSPOR vs NIPER)
4. {nl:,} record HIGH_SYNC_LAG (>30 hari sinkronisasi)

REKOMENDASI DATA GOVERNANCE:
1. Validasi format di titik input OSS & CEISA
2. OSS sebagai System of Record, SLA sinkronisasi CEISA <30 hari
3. Rekonsiliasi bulanan untuk Sync Conflict & Logical Conflict
4. Jadwalkan ulang pipeline MDM secara periodik
5. Tetapkan data steward per domain
''')
print('Tahap 6 selesai!')
print('Seluruh pipeline MDM (Tahap 0-6) telah berhasil dijalankan!')"""))

# ================================================================
# CLOSING
# ================================================================
cells.append(md_cell("""<div style="background:linear-gradient(135deg,#1A237E,#283593);padding:30px;border-radius:15px;color:white;text-align:center;margin:20px 0">
<h1 style="color:#FFD54F">SELESAI!</h1>
<h2 style="color:white">Pipeline MDM End-to-End Berhasil Dijalankan</h2>
<div style="background:rgba(255,255,255,0.1);border-radius:10px;padding:20px;max-width:600px;margin:0 auto">
<p style="margin:0;line-height:2">
Tahap 0 - Simulasi Data & Faker Engine<br>
Tahap 1 - Data Profiling (Baseline DQ)<br>
Tahap 2 - Data Cleansing & Standardization<br>
Tahap 3 - Duplicate Detection & Matching<br>
Tahap 4 - Golden Record & Survivorship<br>
Tahap 5 - Data Quality Monitoring<br>
Tahap 6 - YData Profiling Dashboard
</p>
</div>
<p style="margin-top:20px;opacity:0.9">Output: /content/data/ dan /content/reports/</p>
</div>

---

### Struktur Output

```
/content/
data/
  raw/oss_nib_data.csv, ceisa_data.csv
  processed/oss_cleaned.csv, ceisa_cleaned.csv, dataset_clean.csv
  golden/golden_record.csv
reports/
  profiling_before_oss.html, profiling_before_ceisa.html, profiling_after.html
  audit_trail.csv, provenance_log.csv, conflict_log.csv
  dq_scorecard.csv, dq_rule_results.csv
  candidate_pairs.csv, duplicate_cluster.csv
  *.png
```

**Mini Project - Master Data Management DJBC**
**Kelompok 5 | Single Importer & Exporter View**"""))

# ================================================================
# BUILD NOTEBOOK
# ================================================================
notebook = {
    "nbformat": 4, "nbformat_minor": 5,
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
print(f'Cells: {len(cells)} (md={sum(1 for c in cells if c["cell_type"]=="markdown")}, code={sum(1 for c in cells if c["cell_type"]=="code")})')
print(f'Size: {os.path.getsize(OUTPUT_FILE):,} bytes')

# Quick validation
with open(OUTPUT_FILE, 'r') as f:
    nb = json.load(f)
print(f'Valid JSON: YES')

# Check for remaining issues
for i, c in enumerate(nb['cells']):
    src_str = ''.join(c['source'])
    if 'from Source' in src_str and '#' not in src_str.split('from Source')[0][-3:]:
        print(f'WARNING Cell {i+1}: Possible unfixed Source import')
    if 'matplotlib.use' in src_str and '#' not in src_str:
        print(f'WARNING Cell {i+1}: matplotlib.use not commented')
    if 'reports/' in src_str and 'REPORTS_DIR' not in src_str and c['cell_type'] == 'code':
        # Check if it's actually hardcoded
        for line in src_str.split('\n'):
            if "'reports/" in line or '"reports/"' in line:
                if 'REPORTS_DIR' not in line and '#' not in line:
                    print(f'WARNING Cell {i+1}: Hardcoded reports/ path: {line.strip()[:80]}')

print('Done!')
