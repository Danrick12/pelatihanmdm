# ============================================================
# CELL 1: IMPORT LIBRARY & LOAD DATASET
# ============================================================

import pandas as pd
import numpy as np
import re, warnings, json
from datetime import datetime
from faker import Faker
from collections import defaultdict
warnings.filterwarnings('ignore')

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import seaborn as sns

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 140)
pd.set_option('display.max_colwidth', 40)
sns.set_theme(style='whitegrid')
plt.rcParams['figure.figsize'] = (14, 6)

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)
fake = Faker('id_ID')
Faker.seed(RANDOM_SEED)

# ── Load dataset dari LAB 2 & LAB 3 ──
try:
    df_clean    = pd.read_csv('dataset_wp_clean.csv')
    df_clusters = pd.read_csv('duplicate_clusters.csv')
    print(f'✅ dataset_wp_clean.csv    : {df_clean.shape}')
    print(f'✅ duplicate_clusters.csv  : {df_clusters.shape}')
except FileNotFoundError as e:
    print(f'❌ File tidak ditemukan: {e}')
    print('   Pastikan LAB 2 dan LAB 3 sudah selesai dijalankan.')
    raise

# Ringkasan cluster
n_clusters = df_clusters['cluster_id'].nunique()
n_in_cluster = len(df_clusters)
print(f'\n   Total cluster duplikat : {n_clusters:,}')
print(f'   Record dalam cluster   : {n_in_cluster:,}')
print(f'   Record di luar cluster : {len(df_clean) - n_in_cluster:,} (sudah unik)')
print(f'\n   Contoh cluster mapping:')
display(df_clusters.head(8))

# ============================================================
# CELL 2: SIMULASI DATASET SUMBER 1 — SIDJP
# ============================================================

import random
random.seed(RANDOM_SEED)

# Ambil sample 500 WP dari dataset bersih LAB 2 sebagai base
df_base = df_clean.sample(n=500, random_state=RANDOM_SEED).copy().reset_index(drop=True)

def make_sidjp_record(row):
    """
    Buat versi record SIDJP dari base record.
    SIDJP: data formal, casing sering UPPERCASE, update lambat.
    """
    rec = {
        'sumber'          : 'SIDJP',
        'id_sidjp'        : f'SIDJP{row["id_record"][2:]}',
        'npwp'            : row['npwp'],
        'nama_wp'         : row['nama_wp'].upper(),  # SIDJP pakai uppercase
        'jenis_wp'        : row['jenis_wp'],
        'status_wp'       : row['status_wp'],
        'status_pkp'      : row['status_pkp'],
        'kode_kpp'        : row['kode_kpp'],
        'nama_kpp'        : row['nama_kpp'],
        'kode_provinsi'   : row['kode_provinsi'],
        'nama_provinsi'   : row['nama_provinsi'],
        'alamat'          : row['alamat'].upper() if pd.notna(row['alamat']) else None,
        'kota'            : row['kota'],
        'kode_pos'        : row['kode_pos'],
        'klu_kode'        : row['klu_kode'],
        'klu_nama'        : row['klu_nama'],
        # SIDJP: email sering kosong (tidak dikumpulkan)
        'email'           : None if random.random() < 0.4 else row['email'],
        # SIDJP: telepon ada tapi mungkin lama
        'telepon'         : row['telepon'],
        'penghasilan'     : row['penghasilan'],
        'tanggal_daftar'  : row['tanggal_daftar'],
        'tanggal_update'  : '2022-01-01',  # SIDJP: update terakhir 2022
        'nik'             : row['nik'],
        'skor_kelengkapan': random.uniform(0.65, 0.90),
    }
    return rec

sidjp_records = [make_sidjp_record(row) for _, row in df_base.iterrows()]
df_sidjp = pd.DataFrame(sidjp_records)

print(f'✅ Dataset SIDJP berhasil dibuat: {df_sidjp.shape}')
print(f'   Kolom: {list(df_sidjp.columns)}')
print(f'\nContoh 3 record SIDJP:')
display(df_sidjp[['id_sidjp','npwp','nama_wp','email','telepon','tanggal_update']].head(3))

# ============================================================
# CELL 3: SIMULASI DATASET SUMBER 2 — e-FILING
# ============================================================

def make_efiling_record(row):
    """
    Buat versi record e-Filing dari base record.
    e-Filing: self-reported, lebih up-to-date, format tidak konsisten.
    """
    # Simulasi variasi nama di e-Filing (Title Case tapi kadang typo kecil)
    nama = row['nama_wp']
    if random.random() < 0.15:
        # Typo kecil: tambah/kurang huruf atau spasi
        chars = list(nama)
        pos   = random.randint(0, max(0, len(chars)-2))
        if random.random() < 0.5 and len(chars) > 3:
            chars.pop(pos)   # hapus satu karakter
        else:
            chars.insert(pos, ' ')  # tambah spasi
        nama = ''.join(chars).strip()

    # e-Filing: alamat sering diisi manual oleh WP — format berbeda
    alamat = row['alamat']
    if pd.notna(alamat) and random.random() < 0.3:
        alamat = alamat.lower()  # WP kadang isi lowercase

    rec = {
        'sumber'          : 'EFILING',
        'id_efiling'      : f'EF{row["id_record"][2:]}',
        'npwp'            : row['npwp'],
        'nama_wp'         : nama,  # Title Case dengan kemungkinan typo
        'jenis_wp'        : row['jenis_wp'],
        'status_wp'       : row['status_wp'],
        'status_pkp'      : row['status_pkp'],
        'kode_kpp'        : row['kode_kpp'],
        'nama_kpp'        : row['nama_kpp'],
        'kode_provinsi'   : row['kode_provinsi'],
        'nama_provinsi'   : row['nama_provinsi'],
        'alamat'          : alamat,
        'kota'            : row['kota'],
        'kode_pos'        : row['kode_pos'],
        'klu_kode'        : row['klu_kode'],
        'klu_nama'        : row['klu_nama'],
        # e-Filing: email lebih lengkap (WP isi sendiri)
        'email'           : row['email'] if pd.notna(row['email']) else fake.email(),
        # e-Filing: telepon lebih baru
        'telepon'         : fake.phone_number() if random.random() < 0.3 else row['telepon'],
        'penghasilan'     : row['penghasilan'] * random.uniform(0.95, 1.05),  # sedikit beda
        'tanggal_daftar'  : row['tanggal_daftar'],
        'tanggal_update'  : '2024-06-15',  # e-Filing: lebih baru (2024)
        'nik'             : row['nik'],
        'skor_kelengkapan': random.uniform(0.70, 0.95),
    }
    return rec

efiling_records = [make_efiling_record(row) for _, row in df_base.iterrows()]
df_efiling = pd.DataFrame(efiling_records)

print(f'✅ Dataset e-Filing berhasil dibuat: {df_efiling.shape}')
print(f'\nContoh 3 record e-Filing:')
display(df_efiling[['id_efiling','npwp','nama_wp','email','telepon','tanggal_update']].head(3))

# ── Tampilkan perbandingan side-by-side ──
print(f'\n📊 PERBANDINGAN DATA SIDJP vs e-FILING (sample 3 WP):')
for i in range(3):
    s = df_sidjp.iloc[i]
    e = df_efiling.iloc[i]
    print(f'\n  WP #{i+1} — NPWP: {s["npwp"]}')
    print(f'    Nama SIDJP  : {s["nama_wp"]}')
    print(f'    Nama eFiling: {e["nama_wp"]}')
    print(f'    Email SIDJP : {s["email"]}')
    print(f'    Email eFiling: {e["email"]}')
    print(f'    Update SIDJP : {s["tanggal_update"]}  |  Update eFiling: {e["tanggal_update"]}')

# ============================================================
# CELL 4: DEFINISI SURVIVORSHIP RULES
# Setiap field memiliki aturan berbeda berdasarkan logika bisnis
# ============================================================

# Prioritas sumber: sumber mana yang lebih dipercaya per field
SOURCE_PRIORITY = {
    'SIDJP'  : 1,   # prioritas tertinggi untuk data formal
    'EFILING': 2,   # prioritas untuk data kontak & penghasilan
}

def rule_most_recent(values_with_source: list) -> tuple:
    """
    Ambil nilai dari sumber yang paling baru diupdate.
    values_with_source: list of (value, source, update_date)
    Returns: (winning_value, winning_source)
    """
    valid = [(v, s, d) for v, s, d in values_with_source if pd.notna(v) and v != '']
    if not valid: return (None, 'N/A')
    # Sort by update_date descending (terbaru menang)
    valid.sort(key=lambda x: str(x[2]), reverse=True)
    return (valid[0][0], valid[0][1])


def rule_most_complete(values_with_source: list) -> tuple:
    """
    Ambil nilai yang paling tidak null dan paling panjang.
    Prioritas: tidak null > terpanjang > sumber terpercaya.
    """
    valid = [(v, s) for v, s, *_ in values_with_source if pd.notna(v) and str(v).strip() != '']
    if not valid: return (None, 'N/A')
    # Ambil yang terpanjang
    valid.sort(key=lambda x: len(str(x[0])), reverse=True)
    return (valid[0][0], valid[0][1])


def rule_trusted_source(values_with_source: list, priority: dict) -> tuple:
    """
    Ambil nilai dari sumber paling tepercaya (priority terendah angkanya).
    Jika sumber prioritas nilainya null, turun ke sumber berikutnya.
    """
    valid = [(v, s) for v, s, *_ in values_with_source if pd.notna(v) and str(v).strip() != '']
    if not valid: return (None, 'N/A')
    # Sort by priority (1=tertinggi, 2=kedua, dst.)
    valid.sort(key=lambda x: priority.get(x[1], 99))
    return (valid[0][0], valid[0][1])


def rule_highest_score(values_with_source: list) -> tuple:
    """
    Ambil nilai dari sumber dengan skor kelengkapan tertinggi.
    """
    # values_with_source: list of (value, source, score)
    valid = [(v, s, sc) for v, s, *rest in values_with_source
             if pd.notna(v) and str(v).strip() != ''
             for sc in (rest[0] if rest else [0.5],)]
    if not valid: return (None, 'N/A')
    valid.sort(key=lambda x: x[2], reverse=True)
    return (valid[0][0], valid[0][1])


# ── Mapping field → survivorship rule yang digunakan ──
FIELD_RULES = {
    # Field identitas formal → prioritaskan SIDJP
    'npwp'          : ('trusted_source', SOURCE_PRIORITY),
    'nama_wp'       : ('trusted_source', SOURCE_PRIORITY),
    'jenis_wp'      : ('trusted_source', SOURCE_PRIORITY),
    'status_wp'     : ('most_recent',    None),
    'status_pkp'    : ('most_recent',    None),
    # Field referensi → sumber tepercaya
    'kode_kpp'      : ('trusted_source', SOURCE_PRIORITY),
    'nama_kpp'      : ('trusted_source', SOURCE_PRIORITY),
    'kode_provinsi' : ('trusted_source', SOURCE_PRIORITY),
    'nama_provinsi' : ('trusted_source', SOURCE_PRIORITY),
    # Field kontak → paling baru
    'email'         : ('most_recent',    None),
    'telepon'       : ('most_recent',    None),
    # Field alamat → paling lengkap
    'alamat'        : ('most_complete',  None),
    'kota'          : ('most_complete',  None),
    'kode_pos'      : ('most_complete',  None),
    # Field KLU → sumber tepercaya
    'klu_kode'      : ('trusted_source', SOURCE_PRIORITY),
    'klu_nama'      : ('trusted_source', SOURCE_PRIORITY),
    # Field finansial → paling baru (e-Filing lebih update)
    'penghasilan'   : ('most_recent',    None),
    # Field tanggal
    'tanggal_daftar': ('trusted_source', SOURCE_PRIORITY),
    # Field identitas pribadi
    'nik'           : ('most_complete',  None),
}

print('✅ Survivorship Rules berhasil didefinisikan!')
print(f'   Total field dengan rule: {len(FIELD_RULES)}')
print(f'\n   Ringkasan rule per field:')
rule_summary = pd.DataFrame([
    {'Field': f, 'Rule': r[0], 'Parameter': str(r[1])[:30] if r[1] else '-'}
    for f, r in FIELD_RULES.items()
])
display(rule_summary)

# ============================================================
# CELL 5: COMBINE DATA DARI DUA SUMBER
# Satukan SIDJP dan e-Filing ke dalam satu dataframe
# ============================================================

# Standardisasi kolom agar bisa digabung
COMMON_FIELDS = [
    'npwp','nama_wp','jenis_wp','status_wp','status_pkp',
    'kode_kpp','nama_kpp','kode_provinsi','nama_provinsi',
    'alamat','kota','kode_pos','klu_kode','klu_nama',
    'email','telepon','penghasilan','tanggal_daftar','nik',
    'sumber','tanggal_update','skor_kelengkapan'
]

# Tambah kolom yang mungkin tidak ada
for df_, name in [(df_sidjp, 'SIDJP'), (df_efiling, 'EFILING')]:
    for col in COMMON_FIELDS:
        if col not in df_.columns:
            df_[col] = None

df_sidjp_std   = df_sidjp[COMMON_FIELDS].copy()
df_efiling_std = df_efiling[COMMON_FIELDS].copy()

# Gabungkan dua sumber
df_combined = pd.concat([df_sidjp_std, df_efiling_std], ignore_index=True)
df_combined['tanggal_update'] = pd.to_datetime(df_combined['tanggal_update'])

print(f'✅ Combined dataset: {df_combined.shape}')
print(f'   Dari SIDJP  : {len(df_sidjp_std):,} record')
print(f'   Dari eFiling: {len(df_efiling_std):,} record')
print(f'   Total gabungan: {len(df_combined):,} record')
print(f'\n   Distribusi sumber:')
print(df_combined['sumber'].value_counts())

# Kelompokkan per NPWP (key untuk merge)
grouped = df_combined.groupby('npwp')
print(f'\n   NPWP unik dalam combined dataset: {len(grouped):,}')
print(f'   NPWP dengan data dari dua sumber: {(grouped.size() > 1).sum():,}')


# ============================================================
# CELL 6: FUNGSI GOLDEN RECORD MERGER
# Inti dari pipeline MDM — menggabungkan n record → 1 golden record
# ============================================================

def create_golden_record(records_df: pd.DataFrame,
                          field_rules: dict,
                          source_priority: dict) -> dict:
    """
    Buat satu Golden Record dari sekelompok record duplikat.

    Parameter:
        records_df    : DataFrame berisi semua record yang akan dimerge
        field_rules   : dict mapping field → (rule_type, parameter)
        source_priority: dict mapping source_name → priority_int

    Returns:
        dict berisi golden record + provenance information
    """
    golden = {}
    provenance = {}  # catat dari mana setiap nilai berasal
    conflicts  = {}  # catat konflik yang terjadi

    for field, (rule_type, param) in field_rules.items():
        if field not in records_df.columns:
            golden[field]     = None
            provenance[field] = 'N/A (kolom tidak ada)'
            continue

        # Kumpulkan semua nilai untuk field ini dari semua sumber
        values_with_meta = []
        for _, row in records_df.iterrows():
            values_with_meta.append((
                row[field],
                row.get('sumber', 'UNKNOWN'),
                row.get('tanggal_update', pd.Timestamp('2000-01-01')),
                row.get('skor_kelengkapan', 0.5)
            ))

        # Deteksi konflik: apakah ada nilai yang berbeda?
        unique_vals = set(
            str(v[0]).strip().upper() for v in values_with_meta
            if pd.notna(v[0]) and str(v[0]).strip() != ''
        )
        has_conflict = len(unique_vals) > 1

        # Terapkan survivorship rule
        if rule_type == 'most_recent':
            winning_val, winning_src = rule_most_recent(
                [(v[0], v[1], v[2]) for v in values_with_meta]
            )
        elif rule_type == 'most_complete':
            winning_val, winning_src = rule_most_complete(
                [(v[0], v[1]) for v in values_with_meta]
            )
        elif rule_type == 'trusted_source':
            winning_val, winning_src = rule_trusted_source(
                [(v[0], v[1]) for v in values_with_meta], param
            )
        elif rule_type == 'highest_score':
            winning_val, winning_src = rule_highest_score(
                [(v[0], v[1], v[3]) for v in values_with_meta]
            )
        else:
            winning_val, winning_src = (None, 'UNKNOWN')

        golden[field]     = winning_val
        provenance[field] = winning_src
        if has_conflict:
            conflicts[field] = {
                'values'  : list(unique_vals),
                'winner'  : winning_src,
                'rule'    : rule_type
            }

    return {
        'golden_record': golden,
        'provenance'   : provenance,
        'conflicts'    : conflicts,
        'source_count' : len(records_df),
        'sources_used' : records_df['sumber'].unique().tolist()
    }


# ── Test pada 1 NPWP untuk verifikasi ──
test_npwp   = df_combined['npwp'].value_counts().index[0]
test_records= df_combined[df_combined['npwp'] == test_npwp]

print(f'🔬 TEST GOLDEN RECORD MERGER:')
print(f'   NPWP test  : {test_npwp}')
print(f'   Sumber data: {test_records["sumber"].tolist()}')
print(f'   Jumlah record: {len(test_records)}')

result = create_golden_record(test_records, FIELD_RULES, SOURCE_PRIORITY)

print(f'\n   GOLDEN RECORD yang dihasilkan:')
for field, val in result['golden_record'].items():
    src = result['provenance'][field]
    conf= '⚠ KONFLIK' if field in result['conflicts'] else ''
    print(f'   {field:<20}: {str(val)[:35]:<35} [dari: {src}] {conf}')

print(f'\n   Konflik yang diselesaikan: {len(result["conflicts"])} field')
for field, c in result['conflicts'].items():
    print(f'   ⚠ {field}: {c["values"]} → pemenang [{c["winner"]}] via rule [{c["rule"]}]')

# ============================================================
# CELL 8: ANALISIS POLA KONFLIK
# ============================================================

if len(df_conflicts) == 0:
    print('ℹ Tidak ada konflik yang terdeteksi dalam dataset ini.')
else:
    print('📊 ANALISIS KONFLIK DATA:')
    print('='*60)

    # Frekuensi konflik per field
    conf_by_field = df_conflicts['field'].value_counts().reset_index()
    conf_by_field.columns = ['Field', 'Jumlah Konflik']
    conf_by_field['Persen WP'] = (conf_by_field['Jumlah Konflik'] / len(df_golden) * 100).round(2)

    print(f'\n   Total konflik       : {len(df_conflicts):,}')
    print(f'   Field berkonflik    : {df_conflicts["field"].nunique()}')
    print(f'   WP dengan konflik   : {df_conflicts["npwp"].nunique():,}')
    print(f'\n   TOP 10 field paling sering konflik:')
    display(conf_by_field.head(10))

    # Distribusi jumlah konflik per WP
    conf_per_wp = df_golden['n_conflicts'].value_counts().sort_index()
    print(f'\n   Distribusi jumlah konflik per WP:')
    for n_conf, count in conf_per_wp.items():
        bar = '█' * int(count / max(conf_per_wp) * 20)
        print(f'   {n_conf} konflik: {count:>5,} WP  {bar}')

    # Visualisasi
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Analisis Konflik Data — Golden Record Simulation', fontweight='bold')

    # Chart 1: Bar konflik per field
    ax1 = axes[0]
    top_fields = conf_by_field.head(8)
    ax1.barh(top_fields['Field'], top_fields['Jumlah Konflik'],
             color='#FF7043', edgecolor='white')
    ax1.set_xlabel('Jumlah Konflik')
    ax1.set_title('TOP 8 Field Paling Sering Konflik')
    for i, (_, row) in enumerate(top_fields.iterrows()):
        ax1.text(row['Jumlah Konflik']+0.1, i, f'{row["Persen WP"]:.1f}%',
                 va='center', fontsize=8)

    # Chart 2: Histogram konflik per WP
    ax2 = axes[1]
    df_golden['n_conflicts'].plot(kind='hist', bins=range(0,
        int(df_golden['n_conflicts'].max())+2), ax=ax2,
        color='#2196F3', edgecolor='white')
    ax2.set_xlabel('Jumlah Field Konflik per WP')
    ax2.set_ylabel('Jumlah WP')
    ax2.set_title('Distribusi Jumlah Konflik per WP')

    plt.tight_layout()
    plt.savefig('chart_conflicts.png', dpi=150, bbox_inches='tight')
    plt.show()
    print('💾 Chart disimpan: chart_conflicts.png')

# ============================================================
# CELL 9: WORKFLOW RESOLUSI KONFLIK MANUAL
# Simulasi proses Data Steward mereview dan memutuskan nilai
# ============================================================

class ConflictResolver:
    """
    Workflow manajemen konflik data untuk Data Steward.
    Dalam implementasi nyata ini akan menjadi UI/form web.
    """
    def __init__(self, conflicts_df: pd.DataFrame, golden_df: pd.DataFrame):
        self.conflicts_df = conflicts_df
        self.golden_df    = golden_df.set_index('gr_npwp')
        self.resolutions  = []

    def get_pending_conflicts(self, field_filter=None, limit=10):
        """Ambil daftar konflik yang belum diselesaikan."""
        pending = self.conflicts_df.copy()
        if field_filter:
            pending = pending[pending['field'] == field_filter]
        return pending.head(limit)

    def resolve(self, npwp: str, field: str,
                chosen_value, reason: str, steward: str):
        """
        Data Steward memutuskan nilai untuk konflik tertentu.
        Mencatat resolusi ke dalam log.
        """
        # Update golden record
        if npwp in self.golden_df.index:
            self.golden_df.at[npwp, field] = chosen_value

        # Catat resolusi
        self.resolutions.append({
            'timestamp' : datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'npwp'      : npwp,
            'field'     : field,
            'chosen_val': chosen_value,
            'reason'    : reason,
            'steward'   : steward,
        })
        print(f'✅ Konflik diselesaikan: [{field}] untuk NPWP {npwp}')
        print(f'   Nilai dipilih: {chosen_value}')
        print(f'   Alasan: {reason}')

    def resolution_report(self):
        """Tampilkan semua resolusi yang telah dilakukan."""
        if not self.resolutions:
            print('Belum ada konflik yang diselesaikan.')
            return pd.DataFrame()
        return pd.DataFrame(self.resolutions)


# Inisialisasi resolver
if len(df_conflicts) > 0:
    resolver = ConflictResolver(df_conflicts, df_golden.copy())

    # Tampilkan konflik yang perlu diselesaikan
    print('📋 KONFLIK YANG PERLU DIREVIEW DATA STEWARD:')
    pending = resolver.get_pending_conflicts(limit=5)
    for _, row in pending.iterrows():
        npwp_short = str(row['npwp'])[:15]
        gr = df_golden[df_golden['gr_npwp']==row['npwp']]
        nama = gr['nama_wp'].values[0] if len(gr)>0 else '-'
        print(f'\n  WP: {nama[:30]} | NPWP: {npwp_short}')
        print(f'  Field  : {row["field"]}')
        print(f'  Nilai  : {row["values"]}')
        print(f'  Pemenang auto: [{row["winner"]}] via rule [{row["rule"]}]')

    # Simulasi resolusi manual oleh Data Steward
    print(f'\n   [SIMULASI] Data Steward menyelesaikan konflik secara manual...')
    if len(pending) > 0:
        first = pending.iloc[0]
        sample_val = first['values'].strip("[]\'\" ").split(',')[0].strip("'\"").strip()
        resolver.resolve(
            npwp    = first['npwp'],
            field   = first['field'],
            chosen_value = sample_val,
            reason  = 'Verifikasi dokumen fisik WP — nilai SIDJP lebih akurat',
            steward = 'Data.Steward.01@djp.go.id'
        )

    print(f'\n   Laporan resolusi:')
    display(resolver.resolution_report())
else:
    print('ℹ Tidak ada konflik yang memerlukan resolusi manual.')

# ============================================================
# CELL 10: PROVENANCE ANALYSIS
# Dari sumber mana setiap field dalam golden record berasal?
# ============================================================

print('📊 ANALISIS PROVENANCE — ASAL-USUL DATA:')
print('='*60)

# Distribusi sumber per field
prov_summary = df_provenance.groupby(['field','source']).size().unstack(fill_value=0)

print(f'   Tabel distribusi sumber per field:')
display(prov_summary)

# Persen kontribusi per sumber
prov_pct = prov_summary.div(prov_summary.sum(axis=1), axis=0) * 100
print(f'\n   Persentase kontribusi per sumber:')
display(prov_pct.round(1))

# Hitung overall dominance per sumber
source_contrib = df_provenance['source'].value_counts(normalize=True) * 100
print(f'\n   Kontribusi keseluruhan per sumber:')
for src, pct in source_contrib.items():
    bar = '█' * int(pct / 3)
    print(f'   {src:<12}: {pct:5.1f}% {bar}')

# Visualisasi stacked bar provenance per field
fig, ax = plt.subplots(figsize=(14, 7))

fields_to_plot = [f for f in FIELD_RULES.keys() if f in prov_pct.index][:12]
prov_plot = prov_pct.loc[fields_to_plot]

colors_src = {'SIDJP':'#1565C0','EFILING':'#2E7D32','N/A':'#9E9E9E','UNKNOWN':'#BDBDBD'}
bottom = np.zeros(len(fields_to_plot))

for src in prov_plot.columns:
    color = colors_src.get(src, '#78909C')
    vals  = prov_plot[src].values
    ax.bar(fields_to_plot, vals, bottom=bottom, label=src, color=color, edgecolor='white')
    # Label di tengah bar jika cukup besar
    for i, (v, b) in enumerate(zip(vals, bottom)):
        if v > 8:
            ax.text(i, b + v/2, f'{v:.0f}%', ha='center', va='center',
                    color='white', fontsize=8, fontweight='bold')
    bottom += vals

ax.set_xlabel('Field')
ax.set_ylabel('Persentase Kontribusi (%)')
ax.set_title('Provenance — Distribusi Sumber Data per Field Golden Record',
             fontsize=13, fontweight='bold')
ax.set_ylim(0, 110)
ax.legend(title='Sumber Data', loc='upper right')
plt.xticks(rotation=30, ha='right')
plt.tight_layout()
plt.savefig('chart_provenance.png', dpi=150, bbox_inches='tight')
plt.show()
print('💾 Chart disimpan: chart_provenance.png')

# ============================================================
# CELL 11: QUALITY VALIDATION GOLDEN RECORD
# ============================================================

print('🔍 QUALITY CHECK — GOLDEN RECORD DATASET:')
print('='*65)

checks = []

# Check 1: Tidak ada duplikat NPWP dalam golden record
n_dup_gr = df_golden['gr_npwp'].duplicated().sum()
checks.append(('NPWP Unik dalam GR', n_dup_gr == 0,
               f'{n_dup_gr} duplikat ditemukan'))

# Check 2: Semua GR punya gr_id
n_no_id = df_golden['gr_id'].isna().sum()
checks.append(('Semua GR punya gr_id', n_no_id == 0,
               f'{n_no_id} GR tanpa id'))

# Check 3: Field kritis terisi
for field in ['nama_wp', 'jenis_wp', 'status_wp', 'kode_kpp']:
    n_null = df_golden[field].isna().sum() if field in df_golden.columns else 0
    checks.append((f'{field} tidak null', n_null == 0,
                   f'{n_null} null ditemukan'))

# Check 4: created_at terisi semua
n_no_ts = df_golden['created_at'].isna().sum()
checks.append(('created_at terisi', n_no_ts == 0,
               f'{n_no_ts} tanpa timestamp'))

# Check 5: source_count >= 1
n_no_src = (df_golden['source_count'] < 1).sum()
checks.append(('source_count >= 1', n_no_src == 0,
               f'{n_no_src} GR tanpa sumber'))

# Tampilkan hasil
all_pass = True
for check_name, passed, detail in checks:
    status = '✅ PASS' if passed else '❌ FAIL'
    if not passed: all_pass = False
    print(f'   {status}  {check_name:<35} | {detail}')

print('='*65)
if all_pass:
    print('   ✅ SEMUA CHECK PASSED — Golden Record siap dipromosikan!')
else:
    print('   ❌ ADA CHECK YANG GAGAL — Perbaiki sebelum export!')

# Statistik ringkasan
print(f'\n📊 STATISTIK GOLDEN RECORD:')
print(f'   Total GR          : {len(df_golden):,}')
print(f'   GR dengan konflik : {(df_golden["n_conflicts"] > 0).sum():,}')
print(f'   Avg konflik / GR  : {df_golden["n_conflicts"].mean():.2f}')
print(f'   GR dari 2 sumber  : {(df_golden["source_count"] > 1).sum():,}')
print(f'   GR dari 1 sumber  : {(df_golden["source_count"] == 1).sum():,}')

# ============================================================
# CELL 12: EXPORT SEMUA OUTPUT LAB 4
# ============================================================

# ── 1. Golden Record Dataset (main output) ──
df_golden.to_csv('golden_record_wp.csv', index=False)
print(f'✅ golden_record_wp.csv       — {len(df_golden):,} golden records')

# ── 2. Provenance Log ──
df_provenance.to_csv('provenance_log.csv', index=False)
print(f'✅ provenance_log.csv         — {len(df_provenance):,} entri provenance')

# ── 3. Conflict Log ──
if len(df_conflicts) > 0:
    df_conflicts.to_csv('conflict_log.csv', index=False)
    print(f'✅ conflict_log.csv           — {len(df_conflicts):,} konflik tercatat')

# ── 4. Summary JSON ──
summary = {
    'lab'            : 'LAB4 — Golden Record Simulation',
    'generated_at'   : datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'total_gr'       : len(df_golden),
    'total_conflicts': len(df_conflicts),
    'sources'        : ['SIDJP', 'EFILING'],
    'survivorship_rules': {f: r[0] for f, r in FIELD_RULES.items()},
}
with open('lab4_summary.json', 'w') as f:
    json.dump(summary, f, indent=2)
print(f'✅ lab4_summary.json          — metadata dan konfigurasi lab')

print(f'\n📄 PREVIEW GOLDEN RECORD (5 baris pertama):')
display(df_golden[['gr_id','gr_npwp','nama_wp','jenis_wp','email',
                    'source_count','sources_used','n_conflicts','created_at']].head(5))

# ============================================================
# CELL 13: VISUALISASI PIPELINE MDM END-TO-END
# Diagram yang merangkum seluruh perjalanan data dari LAB 1-4
# ============================================================

fig = plt.figure(figsize=(18, 9))
fig.patch.set_facecolor('#F8F9FA')
ax  = fig.add_subplot(111)
ax.set_xlim(0, 18); ax.set_ylim(0, 9)
ax.axis('off')
ax.set_facecolor('#F8F9FA')

# ── Fungsi helper untuk menggambar kotak ──
def draw_box(ax, x, y, w, h, label, sublabel, color, text_color='white'):
    rect = plt.Rectangle((x, y), w, h, facecolor=color, edgecolor='white',
                          linewidth=2, zorder=3)
    ax.add_patch(rect)
    ax.text(x+w/2, y+h*0.65, label, ha='center', va='center',
            fontsize=10, fontweight='bold', color=text_color, zorder=4)
    ax.text(x+w/2, y+h*0.3, sublabel, ha='center', va='center',
            fontsize=8, color=text_color, alpha=0.9, zorder=4)

def draw_arrow(ax, x1, y1, x2, y2, label=''):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color='#455A64', lw=2), zorder=5)
    if label:
        # Calculate midpoint for label placement
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        # Place label slightly above the midpoint of the arrow
        ax.text(mid_x, mid_y + 0.15, label, ha='center', va='center',
                fontsize=7.5, color='#455A64', style='italic')

# ── Layer 1: Sumber Data ──
ax.text(4, 8.4, 'SUMBER DATA', ha='center', fontsize=11,
        fontweight='bold', color='#1F4E79')
draw_box(ax, 0.5, 6.8, 3.0, 1.3, 'SIDJP', 'Sistem DJP Utama', '#1565C0')
draw_box(ax, 4.5, 6.8, 3.0, 1.3, 'e-Filing', 'Self-Reporting WP', '#1976D2')

# ── Layer 2: LAB 1 — Profiling ──
draw_arrow(ax, 2.0, 6.0, 2.0, 5.3, 'extract')
draw_arrow(ax, 6.0, 6.0, 6.0, 5.3, 'extract')
draw_box(ax, 0.5, 4.0, 7.0, 1.2, 'LAB 1 — DATA PROFILING',
         'Missing value, duplicate, format validation, DQ score', '#2E75B6')
ax.text(4, 3.7, '📊 DQ Score sebelum: ~88/100', ha='center', fontsize=8.5, color='#455A64')

# ── Layer 3: LAB 2 — Cleansing ──
draw_arrow(ax, 4, 4.0, 4, 3.3, 'clean')
draw_box(ax, 0.5, 2.2, 7.0, 1.0, 'LAB 2 — DATA CLEANSING & STANDARDIZATION',
         'Standardisasi teks, identifier, missing values, outlier', '#375623')
ax.text(4, 1.95, '📊 DQ Score sesudah: ~95/100', ha='center', fontsize=8.5, color='#375623')

# ── LAB 3 — Duplicate Detection ──
draw_arrow(ax, 4, 2.2, 4, 1.5, 'detect')
draw_box(ax, 0.5, 0.5, 7.0, 0.9, 'LAB 3 — DUPLICATE DETECTION & MATCHING',
         'Exact match, fuzzy match, composite score, cluster', '#833C00')

# ── Arrow ke LAB 4 ──
draw_arrow(ax, 7.5, 4.5, 9.5, 4.5, 'merge input')

# ── Layer 4: LAB 4 — Golden Record ──
draw_box(ax, 9.5, 3.5, 4.5, 2.0, 'LAB 4 — GOLDEN RECORD',
         'Survivorship rules, merge, provenance', '#7F6000')
ax.text(11.75, 3.2, '🏆 Single Source of Truth', ha='center',
        fontsize=9, fontweight='bold', color='#7F6000')

# ── Output: Golden Record ──
draw_arrow(ax, 14.0, 4.5, 15.5, 4.5, 'distribute')
draw_box(ax, 15.5, 3.8, 2.0, 1.4, 'MDM HUB', 'Golden Records', '#1F4E79')

# ── Downstream ──
ax.annotate('', xy=(17, 5.5), xytext=(16.5, 5.2),
            arrowprops=dict(arrowstyle='->', color='#78909C', lw=1.5))
ax.annotate('', xy=(17, 4.5), xytext=(17.5, 4.5),
            arrowprops=dict(arrowstyle='->', color='#78909C', lw=1.5))
ax.annotate('', xy=(17, 3.5), xytext=(16.5, 3.8),
            arrowprops=dict(arrowstyle='->', color='#78909C', lw=1.5))
ax.text(17.2, 5.6, 'SIDJP', fontsize=8, color='#455A64')
ax.text(17.7, 4.5, 'e-Billing', fontsize=8, color='#455A64')
ax.text(17.2, 3.4, 'Analytics', fontsize=8, color='#455A64')

# ── Title ──
ax.text(9, 8.6, 'MDM PIPELINE — MASTER DATA WAJIB PAJAK',
        ha='center', fontsize=14, fontweight='bold', color='#1F4E79')
ax.text(9, 8.2, 'Kementerian Keuangan / DJP — Program Pelatihan MDM 2026',
        ha='center', fontsize=10, color='#595959')

# Stats boxes
stats = [
    (10.0, 2.5, f'{len(df_combined):,}\nrecord input'),
    (11.5, 2.5, f'{len(df_golden):,}\ngolden record'),
    (13.0, 2.5, f'{len(df_conflicts):,}\nkonflik'),
]
for sx, sy, slabel in stats:
    ax.text(sx, sy, slabel, ha='center', va='center', fontsize=8.5,
            bbox=dict(boxstyle='round,pad=0.4', facecolor='#EBF3FB', edgecolor='#2E75B6'),
            color='#1F4E79', fontweight='bold')

plt.tight_layout()
plt.savefig('chart_mdm_pipeline.png', dpi=150, bbox_inches='tight')
plt.show()
print('💾 Pipeline diagram disimpan: chart_mdm_pipeline.png')
print('\n🏁 LAB 4 SELESAI! Golden Record siap untuk LAB 5: API & Data Integration')
