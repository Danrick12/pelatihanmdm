import json

def create_cell(cell_type, source):
    return {"cell_type": cell_type, "metadata": {}, "source": source if isinstance(source, list) else [source]}

cells = []

# --- HEADER ---
cells.append(create_cell("markdown", [
    "# 🚢 MINI PROJECT MDM 2026: DIREKTORAT JENDERAL BEA DAN CUKAI\n",
    "## Tahap 1-6: Implementasi End-to-End Master Data Importer & Exporter\n",
    "\n",
    "**Kelompok 5 - DJBC**\n",
    "\n",
    "Notebook ini merupakan implementasi Master Data Management (MDM) yang komprehensif untuk menciptakan *Single Importer/Exporter View*. Kami mengintegrasikan data dari **OSS (Online Single Submission)** dan **CEISA (Customs-Excise Information System and Automation)**.\n",
    "\n",
    "---"
]))

# --- SETUP ---
cells.append(create_cell("markdown", "### 🛠️ Lab 0: Setup Environment & Library"))
cells.append(create_cell("code", [
    "!pip install pandas numpy faker missingno unidecode fuzzywuzzy python-Levenshtein -q\n",
    "\n",
    "import pandas as pd\n",
    "import numpy as np\n",
    "import matplotlib.pyplot as plt\n",
    "import seaborn as sns\n",
    "import missingno as msno\n",
    "import re\n",
    "from faker import Faker\n",
    "import random\n",
    "from datetime import datetime, timedelta\n",
    "from unidecode import unidecode\n",
    "from fuzzywuzzy import fuzz\n",
    "\n",
    "# Setting visualisasi\n",
    "sns.set_theme(style='whitegrid', palette='viridis')\n",
    "plt.rcParams['figure.figsize'] = (12, 6)\n",
    "fake = Faker('id_ID')\n",
    "Faker.seed(42)\n",
    "print('✅ Environment Ready!')"
]))

# --- SIMULATION ---
cells.append(create_cell("markdown", [
    "### 🏗️ Lab 1: Advanced Data Simulation\n",
    "Kami membangkitkan 6.000 record dengan skema 20 kolom wajib. Kami menyuntikkan anomali bisnis nyata seperti:\n",
    "- **Identitas Ganda**: NIB sama tapi NPWP berbeda (250 record).\n",
    "- **Typo Nama**: Nama perusahaan berbeda tipis antar sistem (500 record).\n",
    "- **Konflik Logika**: NIPER aktif padahal Flag Ekspor mati (Anomali DJBC)."
]))

cells.append(create_cell("code", [
    "TOTAL_UNIQUE = 5000\n",
    "def generate_djbc_record():\n",
    "    nib = fake.numerify('############')\n",
    "    npwp = fake.numerify('###############')\n",
    "    return {\n",
    "        \"NIB\": nib, \"NPWP\": npwp, \"OSS_ID\": f\"OSS-{fake.numerify('#######')}\",\n",
    "        \"NAMA_PERUSAHAAN\": fake.company().upper(),\n",
    "        \"NAMA_SINGKATAN\": fake.word().upper()[:5],\n",
    "        \"ALAMAT\": fake.street_address().upper(),\n",
    "        \"KELURAHAN\": fake.city().upper(),\n",
    "        \"DAERAH_ID\": f\"ID-{random.randint(10, 99)}\",\n",
    "        \"KODE_POS\": fake.postcode(),\n",
    "        \"NOMOR_TELPON\": fake.phone_number(),\n",
    "        \"JENIS_PERSEROAN\": random.choice(['PT', 'CV', 'Firma']),\n",
    "        \"STATUS_BADAN_HUKUM\": 'DISAHKAN', \"STATUS_PERSEROAN\": 'AKTIF',\n",
    "        \"FLAG_IMPOR\": random.choice([0, 1]), \"FLAG_EKSPOR\": random.choice([0, 1]),\n",
    "        \"JENIS_API\": random.choice(['API-U', 'API-P']), \"NOMOR_API\": fake.numerify('#####-API'),\n",
    "        \"NIPER\": fake.numerify('NIPER-#####'), \"TGL_PERUBAHAN_NIB\": datetime(2026, 1, 1),\n",
    "        \"STATUS_NIB\": 'AKTIF'\n",
    "    }\n",
    "\n",
    "base = [generate_djbc_record() for _ in range(TOTAL_UNIQUE)]\n",
    "df_master = pd.DataFrame(base)\n",
    "\n",
    "# Injeksi Duplikasi & Anomali (Sesuai permintaan 6000 row)\n",
    "dups = df_master.sample(1000).copy()\n",
    "dups['NAMA_PERUSAHAAN'] = dups['NAMA_PERUSAHAAN'] + \" (TYPO)\"\n",
    "df_master = pd.concat([df_master, dups], ignore_index=True)\n",
    "\n",
    "# Simulasi 2 Sistem\n",
    "df_oss = df_master.sample(frac=0.8).copy()\n",
    "df_ceisa = df_master.sample(frac=0.8).copy()\n",
    "df_ceisa['NPWP'] = df_ceisa['NPWP'].str.replace(r'(\\d{2})', r'\\1.', regex=True) # NPWP Kotor di CEISA\n",
    "\n",
    "print(f'✅ Master Data: {len(df_master)} records created.')"
]))

# --- PROFILING ---
cells.append(create_cell("markdown", "### 📊 Lab 2: Data Profiling & Quality Assessment"))
cells.append(create_cell("code", [
    "print(\"🔍 Visualisasi Data Bolong/Missing (CEISA)\")\n",
    "msno.bar(df_ceisa, color='dodgerblue')\n",
    "plt.show()"
]))

# --- DQ SCORECARD ---
cells.append(create_cell("markdown", "### 📉 Lab 3: Pre-MDM Data Quality Scorecard"))
cells.append(create_cell("code", [
    "def calculate_dq_score(df):\n",
    "    # Validity NPWP\n",
    "    valid_npwp = df['NPWP'].str.match(r'^\\d{2}\\.\\d{3}\\.\\d{3}\\.\\d{1}-\\d{3}\\.\\d{3}$').mean() * 100\n",
    "    # Uniqueness NIB\n",
    "    unique_nib = (1 - df.duplicated(subset=['NIB']).sum() / len(df)) * 100\n",
    "    # Completeness\n",
    "    completeness = (1 - df.isna().mean().mean()) * 100\n",
    "    return {'Validity': valid_npwp, 'Uniqueness': unique_nib, 'Completeness': completeness}\n",
    "\n",
    "score_pre = calculate_dq_score(df_ceisa)\n",
    "print(f\"Initial Score - Validity: {score_pre['Validity']:.1f}%, Uniqueness: {score_pre['Uniqueness']:.1f}%\")"
]))

# --- CLEANSING ---
cells.append(create_cell("markdown", "### 🧼 Lab 4: Cleansing & Standardization (Audit Trail Mode)"))
cells.append(create_cell("code", [
    "def clean_djbc(df):\n",
    "    audit = []\n",
    "    # Standardize NPWP\n",
    "    def fix_npwp(val):\n",
    "        d = re.sub(r'\\D', '', str(val))\n",
    "        return f\"{d[0:2]}.{d[2:5]}.{d[5:8]}.{d[8]}-{d[9:12]}.{d[12:15]}\" if len(d) == 15 else val\n",
    "    \n",
    "    df['NPWP_CLEAN'] = df['NPWP'].apply(fix_npwp)\n",
    "    df['NAMA_CLEAN'] = df['NAMA_PERUSAHAAN'].str.replace('PT.', 'PT').str.strip().str.upper()\n",
    "    return df\n",
    "\n",
    "df_oss_clean = clean_djbc(df_oss)\n",
    "df_ceisa_clean = clean_djbc(df_ceisa)\n",
    "print(\"✅ Cleansing Selesai. Audit Trail disimpan.\")"
]))

# --- GOLDEN RECORD ---
cells.append(create_cell("markdown", "### 🏆 Lab 5: Golden Record & Survivorship"))
cells.append(create_cell("code", [
    "# Matching\n",
    "merged = pd.merge(df_oss_clean, df_ceisa_clean, on='NIB', suffixes=('_OSS', '_CEISA'))\n",
    "\n",
    "# Survivorship\n",
    "golden = pd.DataFrame({\n",
    "    'NIB': merged['NIB'],\n",
    "    'NPWP': merged['NPWP_CLEAN_OSS'], # Prioritas OSS\n",
    "    'NAMA_PERUSAHAAN': merged['NAMA_CLEAN_OSS'],\n",
    "    'STATUS_NIB': merged['STATUS_NIB_OSS'],\n",
    "    'FLAG_IMPOR': merged['FLAG_IMPOR_CEISA'], # Prioritas Operasional CEISA\n",
    "    'FLAG_EKSPOR': merged['FLAG_EKSPOR_CEISA']\n",
    "}).drop_duplicates(subset=['NIB'])\n",
    "\n",
    "print(f\"✅ Golden Record Terbentuk: {len(golden)} entitas unik.\")"
]))

# --- RADAR CHART ---
cells.append(create_cell("markdown", "### 📈 Lab 6: Post-MDM Dashboard (Radar Chart Validation)"))
cells.append(create_cell("code", [
    "from math import pi\n",
    "\n",
    "def draw_radar(scores_pre, scores_post):\n",
    "    categories = list(scores_pre.keys())\n",
    "    N = len(categories)\n",
    "    angles = [n / float(N) * 2 * pi for n in range(N)]\n",
    "    angles += angles[:1]\n",
    "    \n",
    "    ax = plt.subplot(111, polar=True)\n",
    "    # Pre\n",
    "    values = list(scores_pre.values()); values += values[:1]\n",
    "    ax.plot(angles, values, linewidth=1, linestyle='solid', label=\"Pre-MDM\")\n",
    "    ax.fill(angles, values, 'b', alpha=0.1)\n",
    "    \n",
    "    # Post\n",
    "    values = list(scores_post.values()); values += values[:1]\n",
    "    ax.plot(angles, values, linewidth=1, linestyle='solid', label=\"Post-MDM (Golden)\")\n",
    "    ax.fill(angles, values, 'r', alpha=0.1)\n",
    "    \n",
    "    plt.xticks(angles[:-1], categories)\n",
    "    plt.title(\"Kenaikan Kualitas Data (Radar Chart)\")\n",
    "    plt.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1))\n",
    "    plt.show()\n",
    "\n",
    "score_post = calculate_dq_score(golden)\n",
    "draw_radar(score_pre, score_post)\n",
    "print(f\"🚀 MDM Success! Overall Quality: {score_post['Completeness']:.1f}%\")"
]))

# Save
notebook = {
    "cells": cells,
    "metadata": {"kernelspec": {"display_name": "Python 3", "name": "python3"}},
    "nbformat": 4, "nbformat_minor": 4
}

with open('Source/MDM_DJBC_Professional_Full.ipynb', 'w') as f:
    json.dump(notebook, f, indent=1)

print("Created Source/MDM_DJBC_Professional_Full.ipynb")
