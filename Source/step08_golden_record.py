# [TAHAP 4] GOLDEN RECORD & SURVIVORSHIP
# Berdasarkan: docs/tahapan/tahap4_golden_record.md & docs/02_business_rules.md §3
#
# Untuk setiap pasangan match dari Tahap 3 (EXACT_NIB, EXACT_NPWP, FUZZY_MATCH/REVIEW),
# gabungkan record OSS + CEISA menjadi satu Golden Record menggunakan survivorship
# rules (§3.A): Legalitas & Status -> OSS menang (System of Record), Operasional
# (KODE_KANTOR, NOMOR_TELPON, dll) -> CEISA menang. Record yang tidak match (orphan)
# tetap masuk apa adanya dengan SOURCE=OSS_ONLY / CEISA_ONLY.

import pandas as pd
import numpy as np
import re
from datetime import datetime
from fuzzywuzzy import fuzz
from Source.step07_matching import extract_digits, normalize_for_matching, DUMMY_NIB
from Source.step02_reference import STATUS_NIB_POOL

NPWP_PATTERN = re.compile(r'^\d{2}\.\d{3}\.\d{3}\.\d{1}-\d{3}\.\d{3}$')
NIB_PATTERN = re.compile(r'^\d{13}$')


# ============================================================
# LANGKAH 2: SURVIVORSHIP RULES (business_rules §3.A)
# ============================================================
# field_golden -> (kolom_OSS, kolom_CEISA, sumber_menang)
#   'OSS'        : field ada di kedua sumber -> OSS menang (Legalitas & Status / System of Record)
#   'OSS_ONLY'   : field hanya tersedia di OSS (legalitas/perizinan)
#   'CEISA_ONLY' : field hanya tersedia di CEISA (operasional, termasuk KODE_KANTOR & NOMOR_TELPON)

FIELD_RULES = {
    'NIB':                ('NIB', 'NIB', 'OSS'),
    'NPWP':               ('NPWP_PERSEROAN', 'NPWP', 'OSS'),
    'NAMA':               ('NAMA_PERSEROAN', 'NAMA_PERUSAHAAN', 'OSS'),
    'NAMA_SINGKATAN':     ('NAMA_SINGKATAN', None, 'OSS_ONLY'),
    'JENIS_PERSEROAN':    ('JENIS_PERSEROAN', None, 'OSS_ONLY'),
    'STATUS_BADAN_HUKUM': ('STATUS_BADAN_HUKUM', None, 'OSS_ONLY'),
    'STATUS_PERSEROAN':   ('STATUS_PERSEROAN', None, 'OSS_ONLY'),
    'ALAMAT':             ('ALAMAT_PERSEROAN', 'ALAMAT_PERUSAHAAN', 'OSS'),
    'KELURAHAN':          ('KELURAHAN_PERSEROAN', 'KELURAHAN', 'OSS'),
    'DAERAH_ID':          ('PERSEROAN_DAERAH_ID', 'DAERAH_ID', 'OSS'),
    'KODE_POS':           ('KODE_POS_PERSEROAN', 'KODE_POS', 'OSS'),
    'FLAG_IMPOR':         ('FLAG_IMPOR', None, 'OSS_ONLY'),
    'FLAG_EKSPOR':        ('FLAG_EKSPOR', None, 'OSS_ONLY'),
    'JENIS_API':          ('JENIS_API', None, 'OSS_ONLY'),
    'KODE_KANTOR':        (None, 'KODE_KANTOR', 'CEISA_ONLY'),
    'NOMOR_TELPON':       (None, 'NOMOR_TELPON', 'CEISA_ONLY'),
    'KATEGORI':           (None, 'KATEGORI', 'CEISA_ONLY'),
    'NIPER':              (None, 'NIPER', 'CEISA_ONLY'),
    'NOMOR_API':          (None, 'NOMOR_API', 'CEISA_ONLY'),
    'ID_PERUSAHAAN':      (None, 'ID_PERUSAHAAN', 'CEISA_ONLY'),
    'TGL_PERUBAHAN_NIB':  ('TGL_PERUBAHAN_NIB', None, 'OSS_ONLY'),
    'TGL_TERBIT_NIB':     (None, 'TGL_TERBIT_NIB', 'CEISA_ONLY'),
    'TGL_SYNC_OSS':       (None, 'TGL_SYNC_OSS', 'CEISA_ONLY'),
    'STATUS_NIB':         ('STATUS_NIB', 'STATUS_NIB', 'OSS'),
}

META_COLS = [
    'SOURCE', 'MATCH_TYPE', 'SOURCE_COUNT', 'N_CONFLICTS',
    'IS_OUT_OF_SYNC', 'IS_STALE', 'HIGH_SYNC_LAG', 'IS_LOGICAL_CONFLICT_NIPER',
    'CREATED_AT',
]
GOLDEN_COLUMNS = ['GR_ID'] + list(FIELD_RULES.keys()) + META_COLS


# ============================================================
# LANGKAH 3: FUNGSI create_golden_record()
# ============================================================

def create_golden_record(oss_row, ceisa_row, field_rules):
    """Gabungkan satu pasangan (oss_row, ceisa_row) menjadi satu golden record
    berdasarkan field_rules. oss_row/ceisa_row boleh None untuk orphan record."""
    golden = {}
    provenance = {}

    for field, (oss_col, ceisa_col, winner) in field_rules.items():
        oss_val = oss_row[oss_col] if (oss_row is not None and oss_col is not None) else None
        ceisa_val = ceisa_row[ceisa_col] if (ceisa_row is not None and ceisa_col is not None) else None

        if winner == 'CEISA_ONLY':
            if pd.notna(ceisa_val) and str(ceisa_val).strip() != '':
                value, source = ceisa_val, 'CEISA'
            else:
                value, source = None, 'N/A'
        elif winner == 'OSS_ONLY':
            if pd.notna(oss_val) and str(oss_val).strip() != '':
                value, source = oss_val, 'OSS'
            else:
                value, source = None, 'N/A'
        else:  # 'OSS' -> field ada di kedua sumber, OSS menang (System of Record)
            if pd.notna(oss_val) and str(oss_val).strip() != '':
                value, source = oss_val, 'OSS'
            elif pd.notna(ceisa_val) and str(ceisa_val).strip() != '':
                value, source = ceisa_val, 'CEISA'
            else:
                value, source = None, 'N/A'

        golden[field] = value
        provenance[field] = source

    return golden, provenance


def detect_field_conflicts(oss_row, ceisa_row):
    """Bandingkan field yang ada di kedua sumber, kembalikan list konflik
    (field, nilai_oss, nilai_ceisa). Dipakai untuk Langkah 6 - Analisis Pola Konflik."""
    conflicts = []

    # STATUS_NIB - target anomali "Sync Conflict" (tahap0 §4)
    if str(oss_row['STATUS_NIB']).strip() != str(ceisa_row['STATUS_NIB']).strip():
        conflicts.append(('STATUS_NIB', oss_row['STATUS_NIB'], ceisa_row['STATUS_NIB']))

    # NPWP - bedakan konflik NILAI (digit beda) vs konflik FORMAT (digit sama, format beda)
    d_oss, d_ceisa = extract_digits(oss_row['NPWP_PERSEROAN']), extract_digits(ceisa_row['NPWP'])
    if d_oss != d_ceisa:
        conflicts.append(('NPWP_VALUE', oss_row['NPWP_PERSEROAN'], ceisa_row['NPWP']))
    elif str(oss_row['NPWP_PERSEROAN']) != str(ceisa_row['NPWP']):
        conflicts.append(('NPWP_FORMAT', oss_row['NPWP_PERSEROAN'], ceisa_row['NPWP']))

    # NAMA - target anomali "Fuzzy Identity"
    if normalize_for_matching(oss_row['NAMA_PERSEROAN']) != normalize_for_matching(ceisa_row['NAMA_PERUSAHAAN']):
        conflicts.append(('NAMA', oss_row['NAMA_PERSEROAN'], ceisa_row['NAMA_PERUSAHAAN']))

    # ALAMAT
    if normalize_for_matching(oss_row['ALAMAT_PERSEROAN']) != normalize_for_matching(ceisa_row['ALAMAT_PERUSAHAAN']):
        conflicts.append(('ALAMAT', oss_row['ALAMAT_PERSEROAN'], ceisa_row['ALAMAT_PERUSAHAAN']))

    # KELURAHAN, DAERAH_ID, KODE_POS - bandingkan jika kedua sisi terisi
    for oss_col, ceisa_col, field_name in [
        ('KELURAHAN_PERSEROAN', 'KELURAHAN', 'KELURAHAN'),
        ('PERSEROAN_DAERAH_ID', 'DAERAH_ID', 'DAERAH_ID'),
        ('KODE_POS_PERSEROAN', 'KODE_POS', 'KODE_POS'),
    ]:
        v_oss, v_ceisa = oss_row[oss_col], ceisa_row[ceisa_col]
        if pd.notna(v_oss) and pd.notna(v_ceisa) and str(v_oss).strip() != str(v_ceisa).strip():
            conflicts.append((field_name, v_oss, v_ceisa))

    return conflicts


def is_logical_conflict_niper(oss_row, ceisa_row):
    """Anomali 'Logical Conflict': FLAG_EKSPOR (OSS) = 'N' tapi NIPER (CEISA) terisi."""
    niper = ceisa_row['NIPER']
    niper_filled = pd.notna(niper) and str(niper).strip() not in ('', 'nan')
    return bool(oss_row['FLAG_EKSPOR'] == 'N' and niper_filled)


# ============================================================
# LANGKAH 4: PROSES MATCHED PAIRS (batch generation)
# ============================================================

def lookup_oss_row(oss_idx, nib, ceisa_row):
    """Ambil baris OSS berdasarkan NIB. NIB dummy "0000000000000" (anomali NIB Invalid)
    dimiliki banyak baris berbeda -> disambiguasi dengan kemiripan nama ke baris CEISA pasangannya."""
    candidates = oss_idx.loc[[nib]]
    if len(candidates) == 1:
        return candidates.iloc[0]
    # NIB dummy "0000000000000" -> banyak baris dengan index label sama, gunakan posisi (iloc)
    scores = candidates['NAMA_PERSEROAN'].apply(
        lambda nama: fuzz.token_set_ratio(normalize_for_matching(nama), normalize_for_matching(ceisa_row['NAMA_PERUSAHAAN']))
    )
    return candidates.iloc[scores.values.argmax()]


def build_matched_records(df_oss, df_ceisa, candidate_pairs, field_rules):
    # Dedup residu anomali "Duplicate Entry" - 1 NIB OSS hanya 1 baris untuk lookup
    pairs = candidate_pairs.drop_duplicates(subset='NIB_OSS', keep='first')

    oss_idx = df_oss.set_index('NIB', drop=False)
    ceisa_idx = df_ceisa.set_index('ID_PERUSAHAAN', drop=False)

    golden_rows, provenance_rows, conflict_rows = [], [], []

    matched_oss_row_ids = set()

    for _, pair in pairs.iterrows():
        ceisa_row = ceisa_idx.loc[pair['ID_PERUSAHAAN_CEISA']]
        oss_row = lookup_oss_row(oss_idx, pair['NIB_OSS'], ceisa_row)
        matched_oss_row_ids.add(oss_row['_ROW_ID'])

        golden, provenance = create_golden_record(oss_row, ceisa_row, field_rules)

        is_out_of_sync = str(oss_row['STATUS_NIB']).strip() != str(ceisa_row['STATUS_NIB']).strip()
        is_logic_conflict = is_logical_conflict_niper(oss_row, ceisa_row)
        field_conflicts = detect_field_conflicts(oss_row, ceisa_row)
        n_conflicts = len(field_conflicts) + (1 if is_logic_conflict else 0)

        golden.update({
            'SOURCE': 'MATCHED',
            'MATCH_TYPE': pair['match_type'],
            'SOURCE_COUNT': 2,
            'N_CONFLICTS': n_conflicts,
            'IS_OUT_OF_SYNC': is_out_of_sync,          # §3.B - anomali "Sync Conflict"
            'IS_STALE': bool(oss_row['IS_STALE']),     # dibawa dari Tahap 1/2, tidak dihitung ulang
            'HIGH_SYNC_LAG': bool(ceisa_row['HIGH_SYNC_LAG']),
            'IS_LOGICAL_CONFLICT_NIPER': is_logic_conflict,
            'CREATED_AT': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        })
        golden_rows.append(golden)

        for field, source in provenance.items():
            provenance_rows.append({'NIB': golden['NIB'], 'field': field, 'source': source})

        for field, oss_val, ceisa_val in field_conflicts:
            conflict_rows.append({
                'NIB': golden['NIB'], 'field': field,
                'oss_value': oss_val, 'ceisa_value': ceisa_val, 'winner': 'OSS',
            })
        if is_logic_conflict:
            conflict_rows.append({
                'NIB': golden['NIB'], 'field': 'FLAG_EKSPOR_vs_NIPER',
                'oss_value': oss_row['FLAG_EKSPOR'], 'ceisa_value': ceisa_row['NIPER'], 'winner': 'OSS (FLAG_EKSPOR)',
            })

    matched_ceisa_ids = set(pairs['ID_PERUSAHAAN_CEISA'])
    return golden_rows, provenance_rows, conflict_rows, matched_oss_row_ids, matched_ceisa_ids


# ============================================================
# LANGKAH 5: PROSES ORPHAN RECORDS (OSS_ONLY / CEISA_ONLY)
# ============================================================

def build_orphan_records(df_oss, df_ceisa, matched_oss_row_ids, matched_ceisa_ids, field_rules):
    golden_rows, provenance_rows = [], []
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    df_oss_orphan = df_oss[~df_oss['_ROW_ID'].isin(matched_oss_row_ids)]
    for _, oss_row in df_oss_orphan.iterrows():
        golden, provenance = create_golden_record(oss_row, None, field_rules)
        golden.update({
            'SOURCE': 'OSS_ONLY', 'MATCH_TYPE': 'N/A', 'SOURCE_COUNT': 1, 'N_CONFLICTS': 0,
            'IS_OUT_OF_SYNC': False, 'IS_STALE': bool(oss_row['IS_STALE']),
            'HIGH_SYNC_LAG': None, 'IS_LOGICAL_CONFLICT_NIPER': False, 'CREATED_AT': timestamp,
        })
        golden_rows.append(golden)
        for field, source in provenance.items():
            provenance_rows.append({'NIB': golden['NIB'], 'field': field, 'source': source})

    df_ceisa_orphan = df_ceisa[~df_ceisa['ID_PERUSAHAAN'].isin(matched_ceisa_ids)]
    for _, ceisa_row in df_ceisa_orphan.iterrows():
        golden, provenance = create_golden_record(None, ceisa_row, field_rules)
        golden.update({
            'SOURCE': 'CEISA_ONLY', 'MATCH_TYPE': 'N/A', 'SOURCE_COUNT': 1, 'N_CONFLICTS': 0,
            'IS_OUT_OF_SYNC': False, 'IS_STALE': None,
            'HIGH_SYNC_LAG': bool(ceisa_row['HIGH_SYNC_LAG']), 'IS_LOGICAL_CONFLICT_NIPER': False, 'CREATED_AT': timestamp,
        })
        golden_rows.append(golden)
        for field, source in provenance.items():
            provenance_rows.append({'NIB': golden['NIB'], 'field': field, 'source': source})

    return golden_rows, provenance_rows


# ============================================================
# LANGKAH 6: ANALISIS POLA KONFLIK
# ============================================================

def analyze_conflict_patterns(df_conflicts, df_golden):
    n_matched = (df_golden['SOURCE'] == 'MATCHED').sum()
    print(f'\n   Total matched pairs       : {n_matched:,}')
    print(f'   Pairs dengan >=1 konflik   : {(df_golden.loc[df_golden["SOURCE"] == "MATCHED", "N_CONFLICTS"] > 0).sum():,}')

    if df_conflicts.empty:
        print('   (tidak ada konflik field terdeteksi)')
        return

    by_field = df_conflicts['field'].value_counts().reset_index()
    by_field.columns = ['field', 'jumlah_konflik']
    by_field['persen_dari_matched'] = (by_field['jumlah_konflik'] / n_matched * 100).round(2)

    print('\n   Frekuensi konflik per field:')
    for _, row in by_field.iterrows():
        print(f'   {row["field"]:<22} {row["jumlah_konflik"]:>6,}  ({row["persen_dari_matched"]:>5.1f}% dari matched pairs)')

    n_out_of_sync = df_golden['IS_OUT_OF_SYNC'].sum()
    n_logic = df_golden['IS_LOGICAL_CONFLICT_NIPER'].sum()
    print(f'\n   IS_OUT_OF_SYNC (STATUS_NIB beda)        : {n_out_of_sync:,} record')
    print(f'   IS_LOGICAL_CONFLICT (FLAG_EKSPOR vs NIPER): {n_logic:,} record')


# ============================================================
# LANGKAH 7: PROVENANCE ANALYSIS
# ============================================================

def provenance_analysis(df_provenance):
    summary = df_provenance.groupby(['field', 'source']).size().unstack(fill_value=0)
    for src in ['OSS', 'CEISA', 'N/A']:
        if src not in summary.columns:
            summary[src] = 0
    summary = summary[['OSS', 'CEISA', 'N/A']]
    pct = summary.div(summary.sum(axis=1), axis=0) * 100

    print('\n   Distribusi sumber per field (jumlah record):')
    print(summary.to_string())

    overall = df_provenance['source'].value_counts(normalize=True) * 100
    print('\n   Kontribusi keseluruhan per sumber:')
    for src, val in overall.items():
        bar = '#' * int(val / 2)
        print(f'   {src:<6}: {val:5.1f}%  {bar}')

    return summary, pct


# ============================================================
# LANGKAH 8: QUALITY VALIDATION GOLDEN RECORD
# ============================================================

def validate_golden_record(df_golden):
    print('\n   Quality checks:')
    checks = []

    # NIB dummy "0000000000000" (anomali NIB Invalid - Tahap 1 Validitas) secara sah dimiliki
    # banyak perusahaan berbeda -> dikecualikan dari cek keunikan NIB.
    is_dummy = df_golden['NIB'] == DUMMY_NIB
    n_dup_dummy = is_dummy.sum()
    n_dup_other = df_golden.loc[~is_dummy, 'NIB'].duplicated().sum()
    checks.append(('NIB unik (di luar NIB dummy/invalid)', n_dup_other == 0, f'{n_dup_other:,} NIB duplikat'))

    n_nib_invalid = (~df_golden['NIB'].astype(str).str.match(NIB_PATTERN)).sum()
    checks.append(('Format NIB (13 digit)', n_nib_invalid == 0, f'{n_nib_invalid:,} NIB format tidak valid'))

    n_npwp_invalid = (~df_golden['NPWP'].astype(str).str.match(NPWP_PATTERN)).sum()
    checks.append(('Format NPWP (XX.XXX.XXX.X-XXX.XXX)', n_npwp_invalid == 0, f'{n_npwp_invalid:,} NPWP format tidak valid'))

    n_status_invalid = (~df_golden['STATUS_NIB'].isin(STATUS_NIB_POOL)).sum()
    checks.append(('STATUS_NIB valid (AKTIF/DIBEKUKAN/DICABUT)', n_status_invalid == 0, f'{n_status_invalid:,} STATUS_NIB tidak valid'))

    for name, passed, detail in checks:
        status = 'PASS' if passed else 'INFO'
        print(f'   [{status}] {name:<42} | {detail}')

    if n_dup_other > 0:
        print(f'\n   -> {n_dup_other:,} NIB duplikat (di luar dummy) di-drop (keep first).')
        keep_mask = is_dummy | ~df_golden['NIB'].duplicated()
        df_golden = df_golden[keep_mask].reset_index(drop=True)

    if n_dup_dummy > 0:
        print(f'\n   INFO: {n_dup_dummy:,} golden record memiliki NIB dummy "{DUMMY_NIB}"')
        print('         (anomali NIB Invalid "Dummy/Kosong") - tetap dipertahankan sebagai record')
        print('         terpisah (GR_ID unik) karena merepresentasikan perusahaan berbeda.')

    return df_golden


# ============================================================
# MAIN PIPELINE (Langkah 1-9)
# ============================================================

if __name__ == "__main__":
    print('=' * 60)
    print('TAHAP 4: GOLDEN RECORD & SURVIVORSHIP')
    print('=' * 60)

    # Langkah 1: Load data
    df_oss = pd.read_csv('data/processed/oss_cleaned.csv', dtype={'NIB': str, 'NPWP_PERSEROAN': str})
    df_ceisa = pd.read_csv('data/processed/ceisa_cleaned.csv', dtype={'NIB': str, 'NPWP': str})
    candidate_pairs = pd.read_csv('reports/candidate_pairs.csv', dtype={'NIB_OSS': str, 'NIB_CEISA': str})
    df_clusters = pd.read_csv('reports/duplicate_cluster.csv')
    print(f'\n1. Load data: OSS={len(df_oss):,} baris, CEISA={len(df_ceisa):,} baris, candidate_pairs={len(candidate_pairs):,} baris')

    # Dedup residu anomali "Duplicate Entry" di OSS menggunakan duplicate_cluster.csv (Tahap 3
    # langkah 9) - hanya buang baris kedua dari setiap cluster OSS_n (NIB sah, terduplikasi persis).
    # NIB dummy "0000000000000" SENGAJA tidak dianggap "Duplicate Entry" (lihat step07: cluster_oss_duplicates
    # mengecualikan DUMMY_NIB) karena ia merepresentasikan banyak perusahaan BERBEDA dengan NIB tidak valid.
    n_before = len(df_oss)
    drop_ids = []
    for _, grp in df_clusters[df_clusters['source'] == 'OSS'].groupby('cluster_id'):
        ids = sorted(grp['record_id'].astype(int).tolist())
        drop_ids.extend(ids[1:])
    df_oss = df_oss.drop(index=drop_ids).reset_index(drop=True)
    df_oss['_ROW_ID'] = df_oss.index  # id unik per baris - NIB dummy "0000000000000" tidak unik
    print(f'   Dedup OSS Duplicate Entry: {n_before:,} -> {len(df_oss):,} baris ({len(drop_ids)} baris duplikat persis dibuang)')

    print('\n2. Survivorship rules (FIELD_RULES) terdefinisi:')
    print(f'   {len(FIELD_RULES)} field di-mapping. OSS=System of Record (legalitas & status),')
    print('   CEISA menang untuk field operasional (KODE_KANTOR, NOMOR_TELPON, KATEGORI, NIPER, NOMOR_API, TGL_SYNC_OSS).')

    # Langkah 4: Proses matched pairs
    print('\n4. Proses matched pairs (EXACT_NIB, EXACT_NPWP, FUZZY_MATCH/REVIEW)...')
    matched_rows, prov_rows_m, conflict_rows, matched_oss_nibs, matched_ceisa_ids = build_matched_records(
        df_oss, df_ceisa, candidate_pairs, FIELD_RULES
    )
    print(f'   {len(matched_rows):,} golden record terbentuk dari matched pairs')

    # Langkah 5: Proses orphan records
    print('\n5. Proses orphan records (OSS_ONLY / CEISA_ONLY)...')
    orphan_rows, prov_rows_o = build_orphan_records(df_oss, df_ceisa, matched_oss_nibs, matched_ceisa_ids, FIELD_RULES)
    n_oss_only = sum(1 for r in orphan_rows if r['SOURCE'] == 'OSS_ONLY')
    n_ceisa_only = sum(1 for r in orphan_rows if r['SOURCE'] == 'CEISA_ONLY')
    print(f'   OSS_ONLY   : {n_oss_only:,} record')
    print(f'   CEISA_ONLY : {n_ceisa_only:,} record')

    # Gabungkan semua golden record + assign GR_ID
    all_rows = matched_rows + orphan_rows
    df_golden = pd.DataFrame(all_rows)
    df_golden.insert(0, 'GR_ID', [f'GR{i:06d}' for i in range(1, len(df_golden) + 1)])
    df_golden = df_golden[GOLDEN_COLUMNS]

    df_provenance = pd.DataFrame(prov_rows_m + prov_rows_o)
    df_conflicts = pd.DataFrame(conflict_rows, columns=['NIB', 'field', 'oss_value', 'ceisa_value', 'winner'])

    # Langkah 6: Analisis pola konflik
    print('\n6. Analisis pola konflik OSS vs CEISA...')
    analyze_conflict_patterns(df_conflicts, df_golden)

    # Langkah 7: Provenance analysis
    print('\n7. Provenance analysis...')
    provenance_analysis(df_provenance)

    # Langkah 8: Quality validation
    print('\n8. Quality validation golden record...')
    df_golden = validate_golden_record(df_golden)

    # Langkah 9: Export
    print('\n9. Export hasil...')
    df_golden.to_csv('data/golden/golden_record.csv', index=False)
    print(f'   data/golden/golden_record.csv -> {len(df_golden):,} golden records')

    df_provenance.to_csv('reports/provenance_log.csv', index=False)
    print(f'   reports/provenance_log.csv    -> {len(df_provenance):,} entri provenance')

    df_conflicts.to_csv('reports/conflict_log.csv', index=False)
    print(f'   reports/conflict_log.csv      -> {len(df_conflicts):,} konflik tercatat')

    print('\n' + '=' * 60)
    print('RINGKASAN')
    print('=' * 60)
    print(f'Total golden record   : {len(df_golden):,}')
    print(f'  - MATCHED           : {(df_golden["SOURCE"] == "MATCHED").sum():,}')
    print(f'  - OSS_ONLY          : {(df_golden["SOURCE"] == "OSS_ONLY").sum():,}')
    print(f'  - CEISA_ONLY        : {(df_golden["SOURCE"] == "CEISA_ONLY").sum():,}')
    print(f'IS_OUT_OF_SYNC        : {df_golden["IS_OUT_OF_SYNC"].sum():,}')
    print(f'IS_STALE              : {(df_golden["IS_STALE"] == True).sum():,}')
    print(f'HIGH_SYNC_LAG         : {(df_golden["HIGH_SYNC_LAG"] == True).sum():,}')
    print(f'IS_LOGICAL_CONFLICT   : {df_golden["IS_LOGICAL_CONFLICT_NIPER"].sum():,}')
    print('=' * 60)
