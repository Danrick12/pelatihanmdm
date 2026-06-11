# ============================================================
# CELL 1: INSTALL LIBRARY LAB 3
# ============================================================

!pip install recordlinkage fuzzywuzzy python-Levenshtein jellyfish -q
!pip install networkx -q   # untuk visualisasi cluster duplikat

print('✅ Library berhasil diinstall:')
print('   recordlinkage : framework record linkage & deduplication')
print('   fuzzywuzzy    : fuzzy string matching (token sort, partial ratio)')
print('   jellyfish     : Jaro-Winkler, Soundex, Levenshtein distance')
print('   networkx      : analisis dan visualisasi graf duplikat cluster')

# ============================================================
# CELL 2: IMPORT LIBRARY & LOAD DATASET
# ============================================================

import pandas as pd
import numpy as np
import re, warnings, time
from datetime import datetime
from itertools import combinations
warnings.filterwarnings('ignore')

# String matching
from fuzzywuzzy import fuzz, process
import jellyfish
import recordlinkage
from recordlinkage.index import Block, SortedNeighbourhood

# Graf dan visualisasi
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 140)
sns.set_theme(style='whitegrid')
plt.rcParams['figure.figsize'] = (13, 5)

# ── Load dataset LAB 2 ──
try:
    df = pd.read_csv('dataset_wp_clean.csv')
    df['tanggal_daftar'] = pd.to_datetime(df['tanggal_daftar'], errors='coerce')
    print(f'✅ Dataset LAB 2 berhasil dimuat')
    print(f'   Shape  : {df.shape}')
    print(f'   Kolom  : {list(df.columns)}')
except FileNotFoundError:
    print('❌ File tidak ditemukan. Pastikan LAB 2 sudah selesai.')
    raise

# Simpan salinan untuk referensi
df_original = df.copy()
print(f'\n   Contoh data (3 baris pertama):')
display(df[['id_record','npwp','nama_wp','jenis_wp','kode_kpp','status_wp']].head(3))


# ============================================================
# CELL 3: PERSIAPAN MATCHING KEYS
# Buat kolom normalisasi khusus untuk proses matching
# ============================================================

def normalize_for_matching(text) -> str:
    """
    Normalisasi teks khusus untuk matching — lebih agresif dari standardisasi biasa.
    Tujuan: buat dua teks yang 'sama secara semantik' menjadi identik atau hampir identik.
    """
    if pd.isna(text): return ''
    s = str(text).upper()           # uppercase semua
    s = re.sub(r'\bPT\.?\b', 'PT', s)    # hapus titik dari PT.
    s = re.sub(r'\bCV\.?\b', 'CV', s)
    s = re.sub(r'\bUD\.?\b', 'UD', s)
    s = re.sub(r'[^A-Z0-9\s]', '', s) # hapus semua non-alfanumerik
    s = re.sub(r'\s+', ' ', s)         # normalisasi spasi
    return s.strip()

def extract_npwp_digits(npww) -> str:
    """Ekstrak hanya digit dari NPWP — untuk matching tanpa mempedulikan separator."""
    if pd.isna(npww): return ''
    return re.sub(r'\D', '', str(npww))


# Buat kolom kunci matching
df['nama_key']  = df['nama_wp'].apply(normalize_for_matching)
df['npwp_digits']= df['npwp'].apply(extract_npwp_digits)

# Blocking key: 4 karakter pertama nama (untuk efisiensi)
df['nama_block'] = df['nama_key'].str[:4]

# Blocking key: 6 digit pertama NPWP (kode WP)
df['npwp_block'] = df['npwp_digits'].str[:6]

print('✅ Matching keys berhasil dibuat:')
print(f'   nama_key   : nama ternormalisasi (uppercase, tanpa karakter khusus)')
print(f'   npwp_digits: hanya digit NPWP tanpa separator')
print(f'   nama_block : 4 karakter pertama nama (untuk blocking)')
print(f'   npwp_block : 6 digit pertama NPWP (untuk blocking)')
print(f'')
print('Contoh 5 record:')
display(df[['nama_wp','nama_key','npwp','npwp_digits','nama_block','npwp_block']].head(5))

# ============================================================
# CELL 4: EXACT MATCH — NPWP DUPLICATE
# Record dengan digit NPWP identik = kandidat duplikat kuat
# ============================================================

print('🔍 EXACT MATCH — NPWP DUPLICATE:')
print('='*60)

# Gunakan npwp_digits (tanpa separator) untuk menghindari false negative
# karena format separator berbeda antar sistem
npwp_counts = df.groupby('npwp_digits').size().reset_index(name='frekuensi')
npwp_dup    = npwp_counts[npwp_counts['frekuensi'] > 1].sort_values('frekuensi', ascending=False)

print(f'Total NPWP unik          : {len(npwp_counts):,}')
print(f'NPWP dengan duplikat     : {len(npwp_dup):,}')
print(f'Total record terdampak   : {npwp_dup["frekuensi"].sum():,}')
print(f'Persentase duplikat      : {len(df[df["npwp_digits"].isin(npwp_dup["npwp_digits"])])/len(df)*100:.2f}%')

# Buat dataframe kandidat duplikat berdasarkan NPWP
df_npwp_dup = df[df['npwp_digits'].isin(npwp_dup['npwp_digits'])].copy()
df_npwp_dup = df_npwp_dup.sort_values(['npwp_digits','id_record'])

print(f'\n📄 Contoh kelompok NPWP duplikat (tampilkan 2 kelompok):')
top2_npwp = npwp_dup.head(2)['npwp_digits'].tolist()
for npwp in top2_npwp:
    print(f'\n   NPWP Digits: {npwp}')
    sample = df[df['npwp_digits']==npwp][
        ['id_record','npwp','nama_wp','jenis_wp','kode_kpp','status_wp']
    ]
    display(sample)

# Simpan hasil exact match NPWP
df_npwp_dup.to_csv('exact_dup_npwp.csv', index=False)
print(f'\n💾 Hasil exact match NPWP disimpan: exact_dup_npwp.csv')

# ============================================================
# CELL 5: EXACT MATCH — KOMBINASI MULTI-FIELD
# Semakin banyak field yang cocok, semakin yakin ini duplikat
# ============================================================

print('🔍 EXACT MATCH — KOMBINASI MULTI-FIELD:')
print('='*60)

# Definisikan set kombinasi field untuk exact matching
match_configs = [
    {'fields': ['npwp_digits'],                        'label': 'NPWP saja'},
    {'fields': ['nama_key', 'kode_kpp'],               'label': 'Nama + KPP'},
    {'fields': ['npwp_digits', 'nama_key'],            'label': 'NPWP + Nama'},
    {'fields': ['nama_key', 'kode_kpp', 'jenis_wp'],   'label': 'Nama + KPP + Jenis'},
    {'fields': ['npwp_digits', 'nama_key', 'kode_kpp'],'label': 'NPWP + Nama + KPP'},
]

print(f'  {"Kombinasi Field":<30} {"Duplikat":>10}  {"Record":>10}  {"Persen":>8}')
print('-'*65)

exact_results = {}
for cfg in match_configs:
    fields = cfg['fields']
    label  = cfg['label']

    # Hitung duplikat
    grp    = df.groupby(fields).size().reset_index(name='cnt')
    dup    = grp[grp['cnt'] > 1]
    n_dup_keys   = len(dup)
    n_dup_records= df[df.set_index(fields).index.isin(
        dup.set_index(fields).index)].shape[0] if n_dup_keys > 0 else 0
    pct  = n_dup_records / len(df) * 100

    exact_results[label] = {'n_dup_keys':n_dup_keys, 'n_records':n_dup_records, 'pct':pct}
    icon = '🔴' if pct > 5 else '🟡' if pct > 1 else '🟢'
    print(f'  {icon} {label:<28} {n_dup_keys:>10,}  {n_dup_records:>10,}  {pct:>7.2f}%')

print('\n💡 Interpretasi:')
print('   Semakin banyak field yang dikombinasikan → semakin akurat (presisi tinggi)')
print('   Tapi recall bisa lebih rendah (miss duplikat yang data-nya sedikit berbeda)')

# ============================================================
# CELL 6: STANDARD BLOCKING — MENGGUNAKAN recordlinkage
# ============================================================

# Set index dataframe untuk recordlinkage
df_idx = df.set_index('id_record')

print('📊 ANALISIS EFISIENSI BLOCKING:')
print('='*65)

n_records = len(df_idx)
n_brute   = n_records * (n_records - 1) // 2
print(f'   Total record          : {n_records:,}')
print(f'   Perbandingan brute force : {n_brute:,}  (O(n²/2))')
print()

# ── Blocking 1: berdasarkan npwp_block (6 digit pertama NPWP) ──
indexer1 = recordlinkage.Index()
indexer1.block('npwp_block')
candidate_links1 = indexer1.index(df_idx)
n1 = len(candidate_links1)

# ── Blocking 2: berdasarkan nama_block (4 karakter pertama nama) ──
indexer2 = recordlinkage.Index()
indexer2.block('nama_block')
candidate_links2 = indexer2.index(df_idx)
n2 = len(candidate_links2)

# ── Blocking 3: berdasarkan kode_kpp ──
indexer3 = recordlinkage.Index()
indexer3.block('kode_kpp')
candidate_links3 = indexer3.index(df_idx)
n3 = len(candidate_links3)

print(f'   {"Strategi Blocking":<30} {"Kandidat Pasang":>16}  {"Reduksi":>8}')
print('-'*65)

configs = [
    ('Brute Force (tanpa blocking)',  n_brute, 0),
    ('Block: NPWP 6 digit pertama',   n1,      (1-n1/n_brute)*100),
    ('Block: Nama 4 char pertama',    n2,      (1-n2/n_brute)*100),
    ('Block: Kode KPP',              n3,      (1-n3/n_brute)*100),
]
for label, n, red in configs:
    print(f'   {label:<30} {n:>16,}  {red:>7.1f}%')

print(f'\n💡 Blocking "NPWP 6 digit" mereduksi kandidat sebesar {(1-n1/n_brute)*100:.1f}%!')
print(f'   Artinya: dari {n_brute:,} → {n1:,} perbandingan yang perlu dilakukan.')

import recordlinkage

# ============================================================
# CELL 7: SORTED NEIGHBOURHOOD BLOCKING
# Lebih toleran terhadap variasi kecil pada blocking key
# ============================================================

# Sorted Neighbourhood: sort berdasarkan blocking key,
# lalu bandingkan record dalam 'window' tertentu
# window=3 artinya: setiap record dibandingkan dengan
#          1 record sebelumnya dan 1 record sesudahnya

print('📊 SORTED NEIGHBOURHOOD BLOCKING:')

# Remove even number 2 from the window list
for window in [3, 5]:
    indexer_sn = recordlinkage.Index()
    indexer_sn.sortedneighbourhood('nama_key', window=window)
    links_sn   = indexer_sn.index(df_idx)
    reduksi    = (1 - len(links_sn)/n_brute) * 100
    print(f'   Window={window}: {len(links_sn):>8,} kandidat pasang  (reduksi {reduksi:.1f}%)')

# Gunakan window=3 sebagai kandidat utama untuk fuzzy matching
indexer_main = recordlinkage.Index()
indexer_main.block('npwp_block')   # primary blocking: NPWP
candidate_pairs = indexer_main.index(df_idx)

print(f'\n✅ Kandidat pairs untuk fuzzy matching: {len(candidate_pairs):,} pasang')
print(f'   (menggunakan blocking: 6 digit pertama NPWP)')

# Preview beberapa kandidat pairs
print(f'\n   Contoh 5 kandidat pasang:')
for i, (idx1, idx2) in enumerate(candidate_pairs[:5]):
    r1 = df_idx.loc[idx1]
    r2 = df_idx.loc[idx2]
    print(f'   [{i+1}] {idx1} ({r1["nama_wp"][:25]:<25}) <-> {idx2} ({r2["nama_wp"][:25]})')# ============================================================
# CELL 8: EKSPLORASI ALGORITMA STRING SIMILARITY
# Bandingkan output setiap algoritma pada pasang contoh
# ============================================================

def compute_all_similarities(s1: str, s2: str) -> dict:
    """
    Hitung semua metrik similarity antara dua string.
    Semua nilai dinormalisasi ke rentang [0, 1] atau [0, 100].
    """
    s1_n = normalize_for_matching(s1)  # pakai fungsi dari Cell 3
    s2_n = normalize_for_matching(s2)

    # Jaro-Winkler: rentang 0-1, makin tinggi makin mirip
    jaro_winkler = jellyfish.jaro_winkler_similarity(s1_n, s2_n)

    # Levenshtein: makin kecil makin mirip, normalisasi ke 0-1
    lev_dist = jellyfish.levenshtein_distance(s1_n, s2_n)
    max_len  = max(len(s1_n), len(s2_n)) if max(len(s1_n),len(s2_n))>0 else 1
    lev_sim  = 1 - (lev_dist / max_len)

    # FuzzyWuzzy: rentang 0-100
    token_sort = fuzz.token_sort_ratio(s1_n, s2_n) / 100
    token_set  = fuzz.token_set_ratio(s1_n, s2_n)  / 100
    partial    = fuzz.partial_ratio(s1_n, s2_n)    / 100
    ratio      = fuzz.ratio(s1_n, s2_n)             / 100

    # Soundex: kode fonetik (sama=1, beda=0)
    soundex_match = int(jellyfish.soundex(s1_n[:4] if s1_n else 'X') ==
                        jellyfish.soundex(s2_n[:4] if s2_n else 'Y'))

    return {
        'Jaro-Winkler'  : round(jaro_winkler, 4),
        'Levenshtein'   : round(lev_sim, 4),
        'Token Sort'    : round(token_sort, 4),
        'Token Set'     : round(token_set, 4),
        'Partial Ratio' : round(partial, 4),
        'Simple Ratio'  : round(ratio, 4),
        'Soundex Match' : soundex_match,
    }


# ── Test pada pasang string yang beragam tingkat kemiripannya ──
test_pairs = [
    ('PT. Maju Bersama',    'PT MAJU BERSAMA',         'Sangat mirip — format berbeda'),
    ('PT. Maju Bersama',    'PT. Maju Bersama Jaya',   'Mirip — kata tambahan'),
    ('Budi Santoso',        'Budi Santosa',             'Hampir sama — 1 karakter berbeda'),
    ('PT. Jaya Makmur',     'PT Makmur Jaya',           'Mirip — urutan kata berbeda'),
    ('Koperasi Sejahtera',  'CV Sejahtera Mandiri',     'Agak mirip — beda entitas'),
    ('PT. Berkah Abadi',    'UD. Maju Terus Pantang',   'Berbeda — tidak berhubungan'),
]

print('📊 PERBANDINGAN ALGORITMA SIMILARITY:')
print('='*80)

rows = []
for s1, s2, label in test_pairs:
    sims = compute_all_similarities(s1, s2)
    row  = {'Pasang': f'{s1[:20]} | {s2[:20]}', 'Kasus': label}
    row.update(sims)
    rows.append(row)

sim_df = pd.DataFrame(rows)
display(sim_df.set_index('Pasang'))

print('\n💡 Observasi:')
print('   • Jaro-Winkler sangat baik untuk nama dengan typo kecil')
print('   • Token Sort menangani urutan kata berbeda dengan baik')
print('   • Token Set toleran terhadap kata tambahan (subsidiary, Jr., dll.)')
print('   • Tidak ada satu algoritma yang sempurna — kombinasi lebih baik')

# ============================================================
# CELL 9: FUZZY MATCHING PIPELINE
# Hitung similarity untuk setiap kandidat pasang
# ============================================================

print('🔄 Menjalankan fuzzy matching pipeline...')
print(f'   Jumlah kandidat pasang: {len(candidate_pairs):,}')
print(f'   Estimasi waktu: 30-90 detik...')

start_time = time.time()
results    = []

for idx1, idx2 in candidate_pairs:
    r1 = df_idx.loc[idx1]
    r2 = df_idx.loc[idx2]

    # ── Similarity nama ──
    n1_key = r1['nama_key']
    n2_key = r2['nama_key']
    jw_nama      = jellyfish.jaro_winkler_similarity(n1_key, n2_key)
    token_nama   = fuzz.token_sort_ratio(n1_key, n2_key) / 100
    tokenset_nama= fuzz.token_set_ratio(n1_key, n2_key)  / 100

    # ── Similarity NPWP ──
    d1 = r1['npwp_digits']
    d2 = r2['npwp_digits']
    if d1 and d2:
        npwp_sim = 1.0 if d1 == d2 else (
            fuzz.ratio(d1, d2) / 100
        )
    else:
        npwp_sim = 0.0

    # ── Exact match field lain ──
    kpp_match    = 1.0 if r1['kode_kpp']  == r2['kode_kpp']  else 0.0
    jenis_match  = 1.0 if r1['jenis_wp']  == r2['jenis_wp']  else 0.0

    results.append({
        'id_1'         : idx1,
        'id_2'         : idx2,
        'nama_1'       : r1['nama_wp'],
        'nama_2'       : r2['nama_wp'],
        'npwp_1'       : r1['npwp'],
        'npwp_2'       : r2['npwp'],
        'jenis_1'      : r1['jenis_wp'],
        'jenis_2'      : r2['jenis_wp'],
        'kpp_1'        : r1['kode_kpp'],
        'kpp_2'        : r2['kode_kpp'],
        'sim_nama_jw'  : round(jw_nama, 4),
        'sim_nama_tok' : round(token_nama, 4),
        'sim_nama_set' : round(tokenset_nama, 4),
        'sim_npwp'     : round(npwp_sim, 4),
        'sim_kpp'      : kpp_match,
        'sim_jenis'    : jenis_match,
    })

elapsed = time.time() - start_time
df_pairs = pd.DataFrame(results)

print(f'\n✅ Fuzzy matching selesai!')
print(f'   Waktu eksekusi  : {elapsed:.1f} detik')
print(f'   Total pairs     : {len(df_pairs):,}')
print(f'   Kecepatan       : {len(df_pairs)/elapsed:.0f} pairs/detik')
print(f'\nContoh 5 hasil pairs:')
display(df_pairs[['id_1','id_2','nama_1','nama_2','sim_nama_jw','sim_nama_tok','sim_npwp']].head())

# ============================================================
# CELL 10: COMPOSITE SIMILARITY SCORE
# Weighted combination dari semua metrik similarity
# ============================================================

# Bobot per field — total harus = 1.0
WEIGHTS = {
    'sim_npwp'     : 0.40,  # NPWP: identifier terkuat
    'sim_nama_set' : 0.35,  # Nama: Token Set Ratio
    'sim_kpp'      : 0.15,  # Kode KPP
    'sim_jenis'    : 0.10,  # Jenis WP
}

assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, 'Total bobot harus = 1.0'

# Hitung composite score
df_pairs['composite_score'] = (
    df_pairs['sim_npwp']     * WEIGHTS['sim_npwp']     +
    df_pairs['sim_nama_set'] * WEIGHTS['sim_nama_set'] +
    df_pairs['sim_kpp']      * WEIGHTS['sim_kpp']      +
    df_pairs['sim_jenis']    * WEIGHTS['sim_jenis']
).round(4)

# Tambahkan kolom nama similarity terbaik (untuk interpretasi)
df_pairs['sim_nama_best'] = df_pairs[
    ['sim_nama_jw','sim_nama_tok','sim_nama_set']
].max(axis=1)

# Sort berdasarkan composite score tertinggi
df_pairs = df_pairs.sort_values('composite_score', ascending=False).reset_index(drop=True)

print('📊 DISTRIBUSI COMPOSITE SCORE:')
print(f'   Min   : {df_pairs["composite_score"].min():.4f}')
print(f'   Max   : {df_pairs["composite_score"].max():.4f}')
print(f'   Mean  : {df_pairs["composite_score"].mean():.4f}')
print(f'   Median: {df_pairs["composite_score"].median():.4f}')
print()

# Distribusi berdasarkan range score
bins   = [0, 0.5, 0.7, 0.8, 0.9, 0.95, 1.01]
labels = ['< 0.5','0.5-0.7','0.7-0.8','0.8-0.9','0.9-0.95','≥ 0.95']
df_pairs['score_range'] = pd.cut(df_pairs['composite_score'], bins=bins, labels=labels, right=False)

dist = df_pairs['score_range'].value_counts().sort_index()
print('   Distribusi berdasarkan rentang score:')
for label, count in dist.items():
    pct = count/len(df_pairs)*100
    bar = '█' * int(pct/2)
    print(f'   {label:<10}: {count:>6,} ({pct:5.1f}%) {bar}')

print(f'\n🔝 TOP 10 CANDIDATE PAIRS (composite score tertinggi):')
display(df_pairs[[
    'id_1','id_2','nama_1','nama_2','sim_npwp',
    'sim_nama_set','sim_kpp','composite_score'
]].head(10))

# ============================================================
# CELL 11: VISUALISASI DISTRIBUSI COMPOSITE SCORE
# ============================================================

fig, axes = plt.subplots(1, 3, figsize=(18, 5))
fig.suptitle('Distribusi Composite Similarity Score', fontsize=14, fontweight='bold')

# ── Chart 1: Histogram distribusi score ──
ax1 = axes[0]
ax1.hist(df_pairs['composite_score'], bins=50, color='#2196F3', edgecolor='white', linewidth=0.5)
ax1.axvline(x=0.80, color='orange', linestyle='--', linewidth=2, label='Threshold 0.80')
ax1.axvline(x=0.95, color='red',    linestyle='--', linewidth=2, label='Threshold 0.95')
ax1.set_xlabel('Composite Score')
ax1.set_ylabel('Frekuensi')
ax1.set_title('Distribusi Score Semua Kandidat Pairs')
ax1.legend(fontsize=9)

# ── Chart 2: CDF (Cumulative Distribution) ──
ax2 = axes[1]
scores_sorted = np.sort(df_pairs['composite_score'])
cdf = np.arange(1, len(scores_sorted)+1) / len(scores_sorted)
ax2.plot(scores_sorted, cdf, color='#4CAF50', linewidth=2)
ax2.axvline(x=0.80, color='orange', linestyle='--', linewidth=1.5, label='0.80')
ax2.axvline(x=0.95, color='red',    linestyle='--', linewidth=1.5, label='0.95')

# Annotasi berapa % pairs di atas threshold
pct_above_080 = (df_pairs['composite_score'] >= 0.80).mean() * 100
pct_above_095 = (df_pairs['composite_score'] >= 0.95).mean() * 100
ax2.annotate(f'{pct_above_080:.1f}% pairs\ndi atas 0.80',
    xy=(0.80, 1-pct_above_080/100), xytext=(0.65, 0.7),
    arrowprops=dict(arrowstyle='->', color='orange'), fontsize=9, color='orange')
ax2.set_xlabel('Composite Score'); ax2.set_ylabel('CDF')
ax2.set_title('CDF — Cumulative Distribution'); ax2.legend()

# ── Chart 3: Scatter sim_npwp vs sim_nama_set ──
ax3 = axes[2]
scatter = ax3.scatter(
    df_pairs['sim_npwp'], df_pairs['sim_nama_set'],
    c=df_pairs['composite_score'], cmap='RdYlGn',
    alpha=0.5, s=10
)
plt.colorbar(scatter, ax=ax3, label='Composite Score')
ax3.axvline(x=0.8, color='gray', linestyle=':', linewidth=1)
ax3.axhline(y=0.8, color='gray', linestyle=':', linewidth=1)
ax3.set_xlabel('Similarity NPWP')
ax3.set_ylabel('Similarity Nama (Token Set)')
ax3.set_title('NPWP Sim vs Nama Sim\n(warna = composite score)')

plt.tight_layout()
plt.savefig('chart_composite_score.png', dpi=150, bbox_inches='tight')
plt.show()
print('💾 Chart disimpan: chart_composite_score.png')

# ============================================================
# CELL 12: THRESHOLD ANALYSIS
# Analisis dampak berbagai nilai threshold
# ============================================================

print('📊 ANALISIS DAMPAK THRESHOLD:')
print('='*65)
print(f'  {"Threshold":>10}  {"MATCH":>8}  {"REVIEW":>8}  {"NON-MATCH":>10}')
print('-'*65)

threshold_results = []
for upper in [0.70, 0.75, 0.80, 0.85, 0.90, 0.95]:
    lower = upper - 0.15  # review zone = 15 poin di bawah upper
    n_match    = (df_pairs['composite_score'] >= upper).sum()
    n_review   = ((df_pairs['composite_score'] >= lower) &
                  (df_pairs['composite_score'] <  upper)).sum()
    n_nonmatch = (df_pairs['composite_score'] <  lower).sum()
    threshold_results.append({
        'Upper':upper, 'Lower':lower,
        'Match':n_match, 'Review':n_review, 'NonMatch':n_nonmatch
    })
    print(f'  upper={upper:.2f}/lower={lower:.2f}  {n_match:>8,}  {n_review:>8,}  {n_nonmatch:>10,}')

# ── Pilih threshold yang digunakan ──
UPPER_THRESHOLD = 0.90  # score >= 0.90 = MATCH (auto-merge)
LOWER_THRESHOLD = 0.75  # score  < 0.75 = NON-MATCH

# Klasifikasikan setiap pair
def classify_pair(score):
    if   score >= UPPER_THRESHOLD: return 'MATCH'
    elif score >= LOWER_THRESHOLD: return 'REVIEW'
    else:                          return 'NON-MATCH'

df_pairs['klasifikasi'] = df_pairs['composite_score'].apply(classify_pair)

klas_counts = df_pairs['klasifikasi'].value_counts()
print(f'\n✅ Threshold yang dipilih: UPPER={UPPER_THRESHOLD}, LOWER={LOWER_THRESHOLD}')
print(f'\n   Hasil klasifikasi:')
for klas, count in klas_counts.items():
    pct  = count/len(df_pairs)*100
    icon = {'MATCH':'🔴','REVIEW':'🟡','NON-MATCH':'🟢'}[klas]
    print(f'   {icon} {klas:<12}: {count:>6,} pairs ({pct:.1f}%)')

# ============================================================
# CELL 13: MANUAL SPOT-CHECK
# Review sample dari tiap zona untuk validasi threshold
# ============================================================

display_cols = ['id_1','id_2','nama_1','nama_2','npwp_1','npwp_2',
                'sim_npwp','sim_nama_set','composite_score','klasifikasi']

for zona in ['MATCH', 'REVIEW', 'NON-MATCH']:
    sample = df_pairs[df_pairs['klasifikasi'] == zona].head(4)
    n_total= (df_pairs['klasifikasi'] == zona).sum()
    icon   = {'MATCH':'🔴','REVIEW':'🟡','NON-MATCH':'🟢'}[zona]
    print(f'\n{icon} ZONA: {zona} ({n_total:,} pairs total)')
    print('='*60)
    for _, row in sample.iterrows():
        print(f'   Score : {row["composite_score"]:.4f}')
        print(f'   Nama 1: {row["nama_1"]}')
        print(f'   Nama 2: {row["nama_2"]}')
        print(f'   NPWP 1: {row["npwp_1"]}  |  NPWP 2: {row["npwp_2"]}')
        print(f'   sim_npwp={row["sim_npwp"]:.2f}  sim_nama={row["sim_nama_set"]:.2f}')
        print()

print('\n💡 INSTRUKSI MANUAL REVIEW:')
print('   1. Lihat zona MATCH — apakah semua memang duplikat? Jika ada false positive,')
print('      naikkan UPPER_THRESHOLD.')
print('   2. Lihat zona NON-MATCH — apakah ada yang seharusnya duplikat? Jika ada,')
print('      turunkan LOWER_THRESHOLD.')
print('   3. Zona REVIEW harus di-review manual oleh Data Steward.')

# ============================================================
# CELL 14: DUPLICATE CLUSTER MENGGUNAKAN GRAPH THEORY
# Node = record WP, Edge = hubungan duplikat (MATCH)
# Connected Component = satu cluster duplikat
# ============================================================

# Ambil pairs yang MATCH saja
df_match = df_pairs[df_pairs['klasifikasi'] == 'MATCH'].copy()

# Buat directed graph
G = nx.Graph()

# Tambahkan semua node (record WP)
G.add_nodes_from(df['id_record'].tolist())

# Tambahkan edge untuk setiap pasang MATCH
for _, row in df_match.iterrows():
    G.add_edge(row['id_1'], row['id_2'],
               weight=row['composite_score'],
               score=row['composite_score'])

# Temukan connected components (= cluster duplikat)
components  = list(nx.connected_components(G))
dup_clusters= [c for c in components if len(c) > 1]  # cluster dengan >1 node

print('📊 DUPLIKATE CLUSTER ANALYSIS:')
print(f'   Total node (record WP)     : {G.number_of_nodes():,}')
print(f'   Total edge (MATCH pairs)   : {G.number_of_edges():,}')
print(f'   Total cluster duplikat     : {len(dup_clusters):,}')
print(f'   Record terdampak (in cluster): {sum(len(c) for c in dup_clusters):,}')
print()

# Distribusi ukuran cluster
cluster_sizes = pd.Series([len(c) for c in dup_clusters])
print('   Distribusi ukuran cluster:')
for size, count in cluster_sizes.value_counts().sort_index().items():
    print(f'   Cluster ukuran {size}: {count} cluster ({count*size} record)')

# ── Tampilkan detail 5 cluster terbesar ──
print(f'\n📄 DETAIL 5 CLUSTER TERBESAR:')
sorted_clusters = sorted(dup_clusters, key=len, reverse=True)

for i, cluster in enumerate(sorted_clusters[:5], 1):
    print(f'\n   Cluster #{i} ({len(cluster)} record):')
    cluster_records = df[df['id_record'].isin(cluster)][
        ['id_record','npwp','nama_wp','jenis_wp','kode_kpp','status_wp']
    ]
    display(cluster_records)

# Simpan hasil cluster ke CSV
cluster_data = []
for cluster_id, cluster in enumerate(sorted_clusters, 1):
    for record_id in cluster:
        cluster_data.append({'cluster_id': cluster_id, 'id_record': record_id,
                             'cluster_size': len(cluster)})
df_clusters = pd.DataFrame(cluster_data)
df_clusters.to_csv('duplicate_clusters.csv', index=False)
print(f'\n💾 Cluster data disimpan: duplicate_clusters.csv')

# ============================================================
# CELL 16: EXPORT LAPORAN AKHIR DUPLICATE DETECTION
# ============================================================

# ── 1. Export semua candidate pairs dengan score ──
df_pairs.to_csv('all_candidate_pairs.csv', index=False)
print(f'✅ all_candidate_pairs.csv    — {len(df_pairs):,} pairs dengan score')

# ── 2. Export MATCH pairs (untuk auto-merge) ──
df_match_export = df_pairs[df_pairs['klasifikasi']=='MATCH'][[
    'id_1','id_2','nama_1','nama_2','npwp_1','npwp_2',
    'sim_npwp','sim_nama_set','sim_kpp','composite_score','klasifikasi'
]]
df_match_export.to_csv('match_pairs_auto_merge.csv', index=False)
print(f'✅ match_pairs_auto_merge.csv  — {len(df_match_export):,} pairs (MATCH, siap auto-merge)')

# ── 3. Export REVIEW pairs (untuk manual review) ──
df_review_export = df_pairs[df_pairs['klasifikasi']=='REVIEW'][[
    'id_1','id_2','nama_1','nama_2','npwp_1','npwp_2',
    'sim_npwp','sim_nama_set','sim_kpp','composite_score','klasifikasi'
]]
df_review_export.to_csv('review_pairs_manual.csv', index=False)
print(f'✅ review_pairs_manual.csv     — {len(df_review_export):,} pairs (perlu review manual)')

# ── 4. Export cluster mapping ──
print(f'✅ duplicate_clusters.csv      — {len(df_clusters):,} records dalam {len(dup_clusters)} cluster')

# ── 5. Executive Summary ──
print(f'\n' + '='*65)
print(f'  EXECUTIVE SUMMARY — DUPLICATE DETECTION LAB 3')
print(f'  Dataset : Master Data Wajib Pajak (LAB 2 output)')
print(f'  Tanggal : {datetime.now().strftime("%Y-%m-%d")}')
print(f'='*65)
print(f'  Total record dianalisis  : {len(df):,}')
print(f'  Kandidat pairs dievaluasi : {len(df_pairs):,}')
print(f'  Threshold MATCH          : composite_score ≥ {UPPER_THRESHOLD}')
print(f'  Threshold REVIEW         : {LOWER_THRESHOLD} ≤ score < {UPPER_THRESHOLD}')
print(f'')
print(f'  HASIL KLASIFIKASI:')
for klas, count in df_pairs["klasifikasi"].value_counts().items():
    pct = count/len(df_pairs)*100
    print(f'    {klas:<12}: {count:>6,} pairs ({pct:.1f}%)')
print(f'')
print(f'  CLUSTER DUPLIKAT : {len(dup_clusters):,} cluster')
print(f'  Record terdampak : {sum(len(c) for c in dup_clusters):,} record')
print(f'  Rekomendasi: {len(df_match_export):,} pairs siap auto-merge,',
      f'{len(df_review_export):,} pairs perlu review manual')
print(f'='*65)
print(f'\n🏁 LAB 3 SELESAI! Output siap untuk LAB 4: Golden Record Simulation')

