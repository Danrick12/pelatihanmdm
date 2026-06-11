# [TAHAP 3] DUPLICATE DETECTION & MATCHING
# Berdasarkan: docs/tahapan/tahap3_duplicate_matching.md & docs/02_business_rules.md §2
#
# Matching utama dilakukan ANTAR DUA DATASET (OSS vs CEISA), bukan dalam satu dataset:
#   1. Exact match NIB      (Prioritas 1)
#   2. Exact match NPWP     (Prioritas 2, untuk sisa yang belum match -> tangkap "NIB Typo")
#   3. Fuzzy match nama/alamat (Prioritas 3, untuk sisa yang belum match)
#   4. Duplicate clustering internal per sumber (OSS: Duplicate Entry by NIB,
#      CEISA: nama/alamat sangat mirip dengan NIB berbeda)

import pandas as pd
import numpy as np
import re
import recordlinkage
from fuzzywuzzy import fuzz
import jellyfish
import networkx as nx
import matplotlib.pyplot as plt

# ============================================================
# KONFIGURASI THRESHOLD & BOBOT (Langkah 6-7)
# ============================================================

UPPER_THRESHOLD = 0.85   # composite_score >= ini      -> FUZZY_MATCH (kandidat valid)
LOWER_THRESHOLD = 0.70   # composite_score <  ini       -> NON_MATCH (dibuang)
                          # di antara keduanya           -> FUZZY_REVIEW (perlu review manual)

# Bobot composite score: NPWP (jika sebagian mirip) + Nama + Alamat, total = 1.0
WEIGHTS = {'npwp': 0.20, 'nama': 0.50, 'alamat': 0.30}

DUMMY_NIB = '0' * 13  # NIB dummy/kosong hasil generate_nib_invalid() - dikecualikan dari exact match


# ============================================================
# LANGKAH 2: PERSIAPAN MATCHING KEYS
# ============================================================

def normalize_for_matching(text):
    """Normalisasi agresif untuk matching: uppercase, normalisasi prefix badan usaha, hapus simbol."""
    if pd.isna(text):
        return ''
    s = str(text).upper()
    for prefix in ['PT', 'CV', 'UD', 'FIRMA', 'PERUM']:
        s = re.sub(rf'\b{prefix}\.?\b', prefix, s)
    s = re.sub(r'[^A-Z0-9\s]', '', s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip()


def extract_digits(value):
    """Ekstrak hanya digit dari sebuah nilai (NIB/NPWP) - tanpa peduli separator."""
    if pd.isna(value):
        return ''
    return re.sub(r'\D', '', str(value))


def prepare_matching_keys(df_oss, df_ceisa):
    """Tambahkan kolom nib_digits, npwp_digits, nama_key, alamat_key, region_key."""
    df_oss = df_oss.copy()
    df_ceisa = df_ceisa.copy()

    df_oss['nib_digits'] = df_oss['NIB'].apply(extract_digits)
    df_oss['npwp_digits'] = df_oss['NPWP_PERSEROAN'].apply(extract_digits)
    df_oss['nama_key'] = df_oss['NAMA_PERSEROAN'].apply(normalize_for_matching)
    df_oss['alamat_key'] = df_oss['ALAMAT_PERSEROAN'].apply(normalize_for_matching)
    df_oss['region_key'] = df_oss['PERSEROAN_DAERAH_ID'].astype(str)

    df_ceisa['nib_digits'] = df_ceisa['NIB'].apply(extract_digits)
    df_ceisa['npwp_digits'] = df_ceisa['NPWP'].apply(extract_digits)
    df_ceisa['nama_key'] = df_ceisa['NAMA_PERUSAHAAN'].apply(normalize_for_matching)
    df_ceisa['alamat_key'] = df_ceisa['ALAMAT_PERUSAHAAN'].apply(normalize_for_matching)
    df_ceisa['region_key'] = df_ceisa['DAERAH_ID'].astype(str)

    return df_oss, df_ceisa


# ============================================================
# LANGKAH 3-4: EXACT MATCHING (NIB -> NPWP)
# ============================================================

def exact_match_nib(df_oss, df_ceisa):
    """Prioritas 1: join OSS-CEISA pada nib_digits (kecuali NIB dummy '0000000000000')."""
    left = df_oss[df_oss['nib_digits'] != DUMMY_NIB]
    right = df_ceisa[df_ceisa['nib_digits'] != DUMMY_NIB]

    merged = left.merge(right, on='nib_digits', suffixes=('_OSS', '_CEISA'))
    merged = merged[merged['nib_digits'] != '']

    return pd.DataFrame({
        'NIB_OSS': merged['NIB_OSS'],
        'ID_PERUSAHAAN_CEISA': merged['ID_PERUSAHAAN'],
        'NIB_CEISA': merged['NIB_CEISA'],
        'match_type': 'EXACT_NIB',
        'similarity_score': 1.0,
    })


def exact_match_npwp(df_oss, df_ceisa):
    """Prioritas 2: untuk sisa yang belum match NIB, join pada npwp_digits.
    Menangkap kasus anomali 'NIB Typo' - NIB beda tapi NPWP sama."""
    merged = df_oss.merge(df_ceisa, on='npwp_digits', suffixes=('_OSS', '_CEISA'))
    merged = merged[merged['npwp_digits'] != '']

    return pd.DataFrame({
        'NIB_OSS': merged['NIB_OSS'],
        'ID_PERUSAHAAN_CEISA': merged['ID_PERUSAHAAN'],
        'NIB_CEISA': merged['NIB_CEISA'],
        'match_type': 'EXACT_NPWP',
        'similarity_score': 1.0,
    })


# ============================================================
# LANGKAH 5-6: FUZZY MATCHING & COMPOSITE SCORE
# ============================================================

def fuzzy_match(remaining_oss, remaining_ceisa):
    """Prioritas 3: blocking per region_key (recordlinkage), lalu hitung composite
    similarity score (NPWP + Nama + Alamat) untuk setiap kandidat pasang."""
    cols = ['NIB_OSS', 'ID_PERUSAHAAN_CEISA', 'NIB_CEISA', 'nama_oss', 'nama_ceisa',
            'sim_npwp', 'sim_nama', 'sim_alamat', 'composite_score']

    if remaining_oss.empty or remaining_ceisa.empty:
        return pd.DataFrame(columns=cols)

    oss_idx = remaining_oss.reset_index(drop=True)
    ceisa_idx = remaining_ceisa.set_index('ID_PERUSAHAAN')

    indexer = recordlinkage.Index()
    indexer.block(left_on='region_key', right_on='region_key')
    candidate_links = indexer.index(oss_idx, ceisa_idx)

    results = []
    for pos, id_perusahaan in candidate_links:
        r1 = oss_idx.loc[pos]
        r2 = ceisa_idx.loc[id_perusahaan]

        # Similarity nama: Jaro-Winkler vs Token Set Ratio, ambil yang terbaik
        sim_nama = max(
            jellyfish.jaro_winkler_similarity(r1['nama_key'], r2['nama_key']),
            fuzz.token_set_ratio(r1['nama_key'], r2['nama_key']) / 100,
        )

        # Similarity alamat: Token Set Ratio
        sim_alamat = fuzz.token_set_ratio(r1['alamat_key'], r2['alamat_key']) / 100

        # Similarity NPWP: 1.0 jika digit identik, partial ratio jika sebagian mirip
        d1, d2 = r1['npwp_digits'], r2['npwp_digits']
        if d1 and d2:
            sim_npwp = 1.0 if d1 == d2 else fuzz.ratio(d1, d2) / 100
        else:
            sim_npwp = 0.0

        composite = (
            sim_npwp * WEIGHTS['npwp']
            + sim_nama * WEIGHTS['nama']
            + sim_alamat * WEIGHTS['alamat']
        )

        results.append({
            'NIB_OSS': r1['NIB'],
            'ID_PERUSAHAAN_CEISA': id_perusahaan,
            'NIB_CEISA': r2['NIB'],
            'nama_oss': r1['NAMA_PERSEROAN'],
            'nama_ceisa': r2['NAMA_PERUSAHAAN'],
            'sim_npwp': round(sim_npwp, 4),
            'sim_nama': round(sim_nama, 4),
            'sim_alamat': round(sim_alamat, 4),
            'composite_score': round(composite, 4),
        })

    return pd.DataFrame(results, columns=cols)


def classify_pair(score):
    if score >= UPPER_THRESHOLD:
        return 'FUZZY_MATCH'
    elif score >= LOWER_THRESHOLD:
        return 'FUZZY_REVIEW'
    else:
        return 'NON_MATCH'


# ============================================================
# LANGKAH 7: VISUALISASI DISTRIBUSI & THRESHOLD ANALYSIS
# ============================================================

def plot_score_distribution(df_fuzzy, output_path='reports/composite_score_distribution.png'):
    if df_fuzzy.empty:
        print('   (tidak ada kandidat fuzzy untuk divisualisasikan)')
        return

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Distribusi Composite Similarity Score (OSS vs CEISA)', fontsize=13, fontweight='bold')

    # Histogram
    ax1 = axes[0]
    ax1.hist(df_fuzzy['composite_score'], bins=30, color='#2196F3', edgecolor='white')
    ax1.axvline(LOWER_THRESHOLD, color='orange', linestyle='--', linewidth=2, label=f'Lower {LOWER_THRESHOLD}')
    ax1.axvline(UPPER_THRESHOLD, color='red', linestyle='--', linewidth=2, label=f'Upper {UPPER_THRESHOLD}')
    ax1.set_xlabel('Composite Score')
    ax1.set_ylabel('Frekuensi')
    ax1.set_title('Histogram Composite Score')
    ax1.legend()

    # CDF
    ax2 = axes[1]
    scores_sorted = np.sort(df_fuzzy['composite_score'])
    cdf = np.arange(1, len(scores_sorted) + 1) / len(scores_sorted)
    ax2.plot(scores_sorted, cdf, color='#4CAF50', linewidth=2)
    ax2.axvline(LOWER_THRESHOLD, color='orange', linestyle='--', linewidth=1.5, label=f'Lower {LOWER_THRESHOLD}')
    ax2.axvline(UPPER_THRESHOLD, color='red', linestyle='--', linewidth=1.5, label=f'Upper {UPPER_THRESHOLD}')
    ax2.set_xlabel('Composite Score')
    ax2.set_ylabel('CDF')
    ax2.set_title('Cumulative Distribution')
    ax2.legend()

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'   Chart disimpan: {output_path}')


def threshold_analysis(df_fuzzy):
    print('\n   Analisis dampak threshold:')
    print(f'   {"Klasifikasi":<14} {"Jumlah":>8}  {"Persen":>8}')
    print('   ' + '-' * 35)
    if df_fuzzy.empty:
        print('   (tidak ada kandidat fuzzy)')
        return
    counts = df_fuzzy['match_type'].value_counts()
    for klas in ['FUZZY_MATCH', 'FUZZY_REVIEW', 'NON_MATCH']:
        n = counts.get(klas, 0)
        pct = n / len(df_fuzzy) * 100
        print(f'   {klas:<14} {n:>8,}  {pct:>7.1f}%')


# ============================================================
# LANGKAH 8: MANUAL SPOT-CHECK
# ============================================================

def spot_check(df_fuzzy, n_sample=3):
    print('\n   Manual spot-check per zona:')
    if df_fuzzy.empty:
        print('   (tidak ada kandidat fuzzy)')
        return

    for zona in ['FUZZY_MATCH', 'FUZZY_REVIEW', 'NON_MATCH']:
        sample = df_fuzzy[df_fuzzy['match_type'] == zona].head(n_sample)
        n_total = (df_fuzzy['match_type'] == zona).sum()
        print(f'\n   --- Zona {zona} ({n_total:,} pairs) ---')
        for _, row in sample.iterrows():
            print(f"     [{row['composite_score']:.4f}] OSS: {row['nama_oss']!r}  <->  CEISA: {row['nama_ceisa']!r} "
                  f"(sim_npwp={row['sim_npwp']:.2f}, sim_nama={row['sim_nama']:.2f}, sim_alamat={row['sim_alamat']:.2f})")


# ============================================================
# LANGKAH 9: DUPLICATE CLUSTERING (INTERNAL PER SUMBER)
# ============================================================

def cluster_oss_duplicates(df_oss):
    """Cluster record OSS dengan nib_digits sama (anomali 'Duplicate Entry')."""
    G = nx.Graph()
    G.add_nodes_from(df_oss.index)

    groups = df_oss[df_oss['nib_digits'] != DUMMY_NIB].groupby('nib_digits').groups
    for nib_digits, idxs in groups.items():
        idxs = list(idxs)
        if len(idxs) < 2:
            continue
        for i in range(len(idxs) - 1):
            G.add_edge(idxs[i], idxs[i + 1])

    components = [c for c in nx.connected_components(G) if len(c) > 1]

    rows = []
    for cid, comp in enumerate(components, 1):
        for idx in comp:
            rows.append({
                'cluster_id': f'OSS_{cid}',
                'source': 'OSS',
                'record_id': idx,
                'NIB': df_oss.loc[idx, 'NIB'],
                'nama': df_oss.loc[idx, 'NAMA_PERSEROAN'],
            })
    return pd.DataFrame(rows, columns=['cluster_id', 'source', 'record_id', 'NIB', 'nama'])


def cluster_ceisa_similar(df_ceisa):
    """Cluster record CEISA dengan nama/alamat sangat mirip TAPI NIB berbeda
    (dedup by NIB sudah selesai di Tahap 2 - fokus ke kandidat lain)."""
    idx_df = df_ceisa.set_index('ID_PERUSAHAAN')

    indexer = recordlinkage.Index()
    indexer.sortedneighbourhood('nama_key', window=5)
    candidate_links = indexer.index(idx_df)

    G = nx.Graph()
    G.add_nodes_from(idx_df.index)

    for id1, id2 in candidate_links:
        r1 = idx_df.loc[id1]
        r2 = idx_df.loc[id2]
        if r1['nib_digits'] == r2['nib_digits']:
            continue  # NIB sama -> sudah ditangani Tahap 2 (Data Mart Dedup)

        sim_nama = fuzz.token_set_ratio(r1['nama_key'], r2['nama_key']) / 100
        sim_alamat = fuzz.token_set_ratio(r1['alamat_key'], r2['alamat_key']) / 100
        composite = sim_nama * 0.6 + sim_alamat * 0.4

        if composite >= UPPER_THRESHOLD:
            G.add_edge(id1, id2)

    components = [c for c in nx.connected_components(G) if len(c) > 1]

    rows = []
    for cid, comp in enumerate(components, 1):
        for record_id in comp:
            rows.append({
                'cluster_id': f'CEISA_{cid}',
                'source': 'CEISA',
                'record_id': record_id,
                'NIB': idx_df.loc[record_id, 'NIB'],
                'nama': idx_df.loc[record_id, 'NAMA_PERUSAHAAN'],
            })
    return pd.DataFrame(rows, columns=['cluster_id', 'source', 'record_id', 'NIB', 'nama'])


# ============================================================
# MAIN PIPELINE (Langkah 1-10)
# ============================================================

if __name__ == "__main__":
    print('=' * 60)
    print('TAHAP 3: DUPLICATE DETECTION & MATCHING')
    print('=' * 60)

    # Langkah 1: Load data
    # NIB dibaca sebagai string supaya leading zero (mis. NIB dummy "0000000000000") tidak hilang
    df_oss = pd.read_csv('data/processed/oss_cleaned.csv', dtype={'NIB': str, 'NPWP_PERSEROAN': str})
    df_ceisa = pd.read_csv('data/processed/ceisa_cleaned.csv', dtype={'NIB': str, 'NPWP': str})
    print(f'\n1. Load data: OSS={len(df_oss):,} baris, CEISA={len(df_ceisa):,} baris')

    # Langkah 2: Persiapan matching keys
    df_oss, df_ceisa = prepare_matching_keys(df_oss, df_ceisa)
    print('2. Matching keys (nib_digits, npwp_digits, nama_key, alamat_key, region_key) dibuat')

    # Langkah 3: Exact match - NIB
    exact_nib_pairs = exact_match_nib(df_oss, df_ceisa)
    matched_oss_nib = set(exact_nib_pairs['NIB_OSS'])
    matched_ceisa_id = set(exact_nib_pairs['ID_PERUSAHAAN_CEISA'])
    print(f'3. Exact match NIB    : {len(exact_nib_pairs):,} pairs')

    remaining_oss = df_oss[~df_oss['NIB'].isin(matched_oss_nib)].copy()
    remaining_ceisa = df_ceisa[~df_ceisa['ID_PERUSAHAAN'].isin(matched_ceisa_id)].copy()

    # Langkah 4: Exact match - NPWP (untuk sisa)
    exact_npwp_pairs = exact_match_npwp(remaining_oss, remaining_ceisa)
    matched_oss_npwp = set(exact_npwp_pairs['NIB_OSS'])
    matched_ceisa_npwp = set(exact_npwp_pairs['ID_PERUSAHAAN_CEISA'])
    print(f'4. Exact match NPWP   : {len(exact_npwp_pairs):,} pairs (anomali NIB Typo)')

    remaining_oss = remaining_oss[~remaining_oss['NIB'].isin(matched_oss_npwp)].copy()
    remaining_ceisa = remaining_ceisa[~remaining_ceisa['ID_PERUSAHAAN'].isin(matched_ceisa_npwp)].copy()
    print(f'   Sisa belum match    : OSS={len(remaining_oss):,}, CEISA={len(remaining_ceisa):,}')

    # Langkah 5: Fuzzy matching
    print('\n5. Fuzzy matching (blocking per region_key)...')
    df_fuzzy = fuzzy_match(remaining_oss, remaining_ceisa)
    print(f'   Kandidat pairs fuzzy: {len(df_fuzzy):,}')

    # Langkah 6: Composite score + klasifikasi
    if not df_fuzzy.empty:
        df_fuzzy['match_type'] = df_fuzzy['composite_score'].apply(classify_pair)
        df_fuzzy = df_fuzzy.sort_values('composite_score', ascending=False).reset_index(drop=True)
    print('6. Composite score & klasifikasi (FUZZY_MATCH/FUZZY_REVIEW/NON_MATCH) selesai')

    # Langkah 7: Visualisasi & threshold analysis
    print('\n7. Visualisasi distribusi composite score...')
    plot_score_distribution(df_fuzzy)
    threshold_analysis(df_fuzzy)

    # Langkah 8: Manual spot-check
    spot_check(df_fuzzy)

    # Langkah 9: Duplicate clustering internal
    print('\n9. Duplicate clustering internal...')
    oss_clusters = cluster_oss_duplicates(df_oss)
    ceisa_clusters = cluster_ceisa_similar(df_ceisa)
    df_clusters = pd.concat([oss_clusters, ceisa_clusters], ignore_index=True)
    print(f'   OSS   : {oss_clusters["cluster_id"].nunique()} cluster ({len(oss_clusters):,} record)')
    print(f'   CEISA : {ceisa_clusters["cluster_id"].nunique()} cluster ({len(ceisa_clusters):,} record)')

    # Langkah 10: Export
    print('\n10. Export hasil...')
    fuzzy_export = pd.DataFrame(columns=['NIB_OSS', 'ID_PERUSAHAAN_CEISA', 'NIB_CEISA', 'match_type', 'similarity_score'])
    if not df_fuzzy.empty:
        fuzzy_export = (
            df_fuzzy[df_fuzzy['match_type'].isin(['FUZZY_MATCH', 'FUZZY_REVIEW'])]
            [['NIB_OSS', 'ID_PERUSAHAAN_CEISA', 'NIB_CEISA', 'match_type', 'composite_score']]
            .rename(columns={'composite_score': 'similarity_score'})
        )

    pair_frames = [df for df in [exact_nib_pairs, exact_npwp_pairs, fuzzy_export] if not df.empty]
    candidate_pairs = pd.concat(pair_frames, ignore_index=True) if pair_frames else fuzzy_export
    candidate_pairs.to_csv('reports/candidate_pairs.csv', index=False)
    print(f'   reports/candidate_pairs.csv  -> {len(candidate_pairs):,} pairs')

    df_clusters.to_csv('reports/duplicate_cluster.csv', index=False)
    print(f'   reports/duplicate_cluster.csv -> {len(df_clusters):,} records')

    # Orphan records (tidak match sama sekali) - kandidat untuk Tahap 4 SOURCE=OSS_ONLY/CEISA_ONLY
    matched_oss_fuzzy = set(fuzzy_export['NIB_OSS'])
    matched_ceisa_fuzzy = set(fuzzy_export['ID_PERUSAHAAN_CEISA'])
    matched_oss_all = matched_oss_nib | matched_oss_npwp | matched_oss_fuzzy
    matched_ceisa_all = matched_ceisa_id | matched_ceisa_npwp | matched_ceisa_fuzzy

    n_orphan_oss = (~df_oss['NIB'].isin(matched_oss_all)).sum()
    n_orphan_ceisa = (~df_ceisa['ID_PERUSAHAAN'].isin(matched_ceisa_all)).sum()

    print('\n' + '=' * 60)
    print('RINGKASAN')
    print('=' * 60)
    print(f'Total candidate pairs   : {len(candidate_pairs):,}')
    print(f'  - EXACT_NIB           : {len(exact_nib_pairs):,}')
    print(f'  - EXACT_NPWP          : {len(exact_npwp_pairs):,}')
    print(f'  - FUZZY (MATCH/REVIEW): {len(fuzzy_export):,}')
    print(f'Orphan records (OSS_ONLY)  : {n_orphan_oss:,}')
    print(f'Orphan records (CEISA_ONLY): {n_orphan_ceisa:,}')
    print(f'Duplicate clusters total   : {df_clusters["cluster_id"].nunique() if not df_clusters.empty else 0}')
    print('=' * 60)
