# [TAHAP 2] DATA CLEANSING & STANDARDIZATION
# Berdasarkan: docs/tahapan/tahap2_cleansing_standardization.md & docs/02_business_rules.md
#
# Pipeline:
#   1. AuditTrail - catat setiap operasi cleansing (apa, berapa baris terdampak)
#   2. Standardisasi NAMA (uppercase, normalisasi prefix PT/CV/UD/Firma/Perum)
#   3. Standardisasi ALAMAT (title case + normalisasi singkatan Jl./No./RT/RW/Kec./Kel.)
#   4. Standardisasi identifier: NIB (13 digit), NPWP (XX.XXX.XXX.X-XXX.XXX),
#      KODE_POS (5 digit), NOMOR_TELPON CEISA (+62...)
#   5. CEISA Data Mart Dedup (1 baris per NIB, snapshot TGL_SYNC_OSS terbaru)
#   6. Missing value handling (wajib: flag saja, opsional: dibiarkan null)
#   7. Validasi referensial PERSEROAN_DAERAH_ID/DAERAH_ID terhadap PROVINSI
#   8. Quality Gate sebelum export
#   9. Export oss_cleaned.csv, ceisa_cleaned.csv, dataset_clean.csv, audit_trail.csv
#  10. Perbandingan skor DQ before vs after (4 dimensi DMBOK)

import pandas as pd
import re
from datetime import datetime

from Source.step02_reference import PROVINSI
from Source.step05_profiling import (
    NIB_PATTERN, NPWP_PATTERN, calculate_dq_metrics,
)

DUMMY_NIB = '0' * 13  # NIB dummy/kosong - sama dengan Source/step07_matching.py

MAND_COLS_OSS = ['NIB', 'NPWP_PERSEROAN', 'NAMA_PERSEROAN', 'STATUS_NIB']
MAND_COLS_CEISA = ['NIB', 'NPWP', 'NAMA_PERUSAHAAN', 'STATUS_NIB']


# ───────────────────────── 1. AUDIT TRAIL ─────────────────────────
class AuditTrail:
    def __init__(self):
        self.entries = []

    def log(self, dataset, operation, field, n_affected, total, description):
        pct = round(n_affected / total * 100, 2) if total else 0.0
        self.entries.append({
            'dataset': dataset,
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'field': field,
            'n_affected': int(n_affected),
            'pct_affected': pct,
            'description': description,
        })

    def to_dataframe(self):
        return pd.DataFrame(self.entries)


# ───────────────────────── 2. STANDARDISASI NAMA ─────────────────────────
def standardize_nama(nama):
    """Uppercase, rapikan spasi, normalisasi prefix PT/CV/UD/Firma/Perum."""
    if pd.isna(nama):
        return nama
    s = re.sub(r'\s+', ' ', str(nama).strip().upper())
    prefix_map = {
        r'^P\.?\s*T\.?\s+': 'PT ',
        r'^C\.?\s*V\.?\s+': 'CV ',
        r'^U\.?\s*D\.?\s+': 'UD ',
        r'^FIRMA\.?\s+': 'FIRMA ',
        r'^PERUM\.?\s+': 'PERUM ',
    }
    for pattern, repl in prefix_map.items():
        s = re.sub(pattern, repl, s)
    return s


# ───────────────────────── 3. STANDARDISASI ALAMAT ─────────────────────────
_ALAMAT_ABBR = {
    r'\bJl\b\.?': 'Jl.',
    r'\bGg\b\.?': 'Gg.',
    r'\bNo\b\.?': 'No.',
    r'\bRt\b\.?': 'RT',
    r'\bRw\b\.?': 'RW',
    r'\bKec\b\.?': 'Kec.',
    r'\bKel\b\.?': 'Kel.',
    r'\bDr\b\.?': 'Dr.',
}


def standardize_alamat(alamat):
    """Title case + normalisasi singkatan (Jl., No., RT/RW, Kec., Kel.)."""
    if pd.isna(alamat):
        return alamat
    s = re.sub(r'\s+', ' ', str(alamat).strip()).title()
    for pattern, repl in _ALAMAT_ABBR.items():
        s = re.sub(pattern, repl, s)
    return s


# ───────────────────────── 4. STANDARDISASI IDENTIFIER ─────────────────────────
def standardize_nib(nib):
    """Hanya digit, pad/trim ke 13 digit."""
    if pd.isna(nib):
        return nib
    digits = re.sub(r'\D', '', str(nib))
    if len(digits) > 13:
        digits = digits[:13]
    elif len(digits) < 13:
        digits = digits.zfill(13)
    return digits


def standardize_npwp(npwp):
    """Format ke XX.XXX.XXX.X-XXX.XXX jika 15 digit; selain itu tetap 'kotor'
    (akan ditandai IS_NPWP_INVALID, sesuai anomali 'Inconsistent NPWP')."""
    if pd.isna(npwp):
        return npwp
    digits = re.sub(r'\D', '', str(npwp))
    if len(digits) == 15:
        return f"{digits[0:2]}.{digits[2:5]}.{digits[5:8]}.{digits[8]}-{digits[9:12]}.{digits[12:15]}"
    return digits


def standardize_kode_pos(kode_pos):
    """Pastikan KODE_POS 5 digit; selain itu dikosongkan (field opsional).
    Catatan: KODE_POS terbaca float64 sehingga leading zero (mis. '08123'
    -> 8123.0) sudah hilang sejak data mentah - nilai seperti ini tidak
    bisa dipastikan 5 digit sehingga ikut dikosongkan."""
    if pd.isna(kode_pos):
        return None
    val = kode_pos
    if isinstance(val, float) and val.is_integer():
        val = int(val)
    digits = re.sub(r'\D', '', str(val))
    if len(digits) == 5:
        return int(digits)
    return None


def standardize_telpon(telp):
    """Normalisasi nomor telepon CEISA ke format +62... (hapus separator,
    kode negara/awalan 0 ganda, dan leading zero pada nomor lokal)."""
    if pd.isna(telp):
        return telp
    digits = re.sub(r'\D', '', str(telp))
    if digits.startswith('62'):
        digits = digits[2:]
    digits = digits.lstrip('0')
    return '+62' + digits


def _kode_pos_changed(before_series, after_series):
    """Hitung baris yang berubah (dikosongkan / nilai berbeda) akibat
    standardisasi KODE_POS."""
    n_changed = 0
    for b, a in zip(before_series, after_series):
        b_blank, a_blank = pd.isna(b), pd.isna(a)
        if b_blank != a_blank:
            n_changed += 1
        elif not b_blank and not a_blank and int(b) != int(a):
            n_changed += 1
    return n_changed


# ───────────────────────── 5. CEISA DATA MART DEDUP ─────────────────────────
def dedup_ceisa(df, audit):
    """1 baris per NIB, sisakan snapshot dengan TGL_SYNC_OSS terbaru.
    NIB dummy ('0'*13) merepresentasikan banyak entitas berbeda yang belum
    punya NIB valid (lihat Source/step07_matching.py: DUMMY_NIB dikecualikan
    dari exact-match), sehingga untuk baris dummy dedup dilakukan per
    ID_PERUSAHAAN (bukan per NIB) agar snapshot duplikat tetap tereliminasi
    tanpa menghapus entitas berbeda."""
    n_before = len(df)
    df = df.copy()
    df['_TGL_SYNC_SORT'] = pd.to_datetime(df['TGL_SYNC_OSS'], errors='coerce')

    is_dummy = df['NIB'] == DUMMY_NIB
    df_real = df[~is_dummy].sort_values('_TGL_SYNC_SORT', ascending=False)
    df_dummy = df[is_dummy].sort_values('_TGL_SYNC_SORT', ascending=False)

    n_multi_nib = (df_real['NIB'].value_counts() > 1).sum()
    df_real_dedup = df_real.drop_duplicates(subset='NIB', keep='first')

    n_multi_id_dummy = (df_dummy['ID_PERUSAHAAN'].value_counts() > 1).sum()
    df_dummy_dedup = df_dummy.drop_duplicates(subset='ID_PERUSAHAAN', keep='first')

    result = pd.concat([df_real_dedup, df_dummy_dedup], ignore_index=True).drop(columns='_TGL_SYNC_SORT')
    n_removed = n_before - len(result)

    audit.log('CEISA', 'DEDUP_SNAPSHOT', 'NIB', n_removed, n_before,
              f"{n_multi_nib} NIB (non-dummy) punya >1 snapshot data mart - disisakan baris "
              f"TGL_SYNC_OSS terbaru; {n_multi_id_dummy} ID_PERUSAHAAN ber-NIB dummy "
              f"({DUMMY_NIB}) juga di-dedup agar ID_PERUSAHAAN tetap unik")
    return result


# ───────────────────────── 8. QUALITY GATE ─────────────────────────
def quality_gate(df, dataset_name, mand_cols):
    print(f"\n--- Quality Gate: {dataset_name} ---")
    issues = []

    nib_invalid = (~df['NIB'].astype(str).str.match(NIB_PATTERN)).sum()
    if nib_invalid:
        issues.append(f"{nib_invalid} NIB tidak 13 digit setelah standardisasi")

    n_incomplete = df[mand_cols].isnull().any(axis=1).sum()
    if n_incomplete:
        issues.append(f"{n_incomplete} baris field wajib masih kosong")

    if dataset_name == 'CEISA':
        non_dummy = df[df['NIB'] != DUMMY_NIB]
        n_dup = non_dummy['NIB'].duplicated().sum()
        if n_dup:
            issues.append(f"{n_dup} NIB (non-dummy) masih duplikat setelah dedup")

    if issues:
        print("STATUS: FAIL")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("STATUS: PASS - tidak ada isu kritis terdeteksi")

    return len(issues) == 0


# ───────────────────────── 10. PERBANDINGAN DQ SCORE ─────────────────────────
def print_dq_comparison(metrics_before, metrics_after, name):
    print(f"\n--- Perbandingan Skor DQ (4 Dimensi DMBOK) — {name} ---")
    print(f"  {'Dimensi':<20}{'Before':>10}{'After':>10}{'Delta':>10}")
    for dim in metrics_before:
        before, after = metrics_before[dim], metrics_after[dim]
        print(f"  {dim:<20}{before:>9.2f}%{after:>9.2f}%{after - before:>+9.2f}%")
    avg_before = sum(metrics_before.values()) / len(metrics_before)
    avg_after = sum(metrics_after.values()) / len(metrics_after)
    print(f"  {'TOTAL DQ SCORE':<20}{avg_before:>9.2f}%{avg_after:>9.2f}%{avg_after - avg_before:>+9.2f}%")


# ───────────────────────── PIPELINE PER DATASET ─────────────────────────
def clean_oss(df_raw, audit):
    df = df_raw.copy()
    n = len(df)

    before = df['NAMA_PERSEROAN'].copy()
    df['NAMA_PERSEROAN'] = df['NAMA_PERSEROAN'].apply(standardize_nama)
    audit.log('OSS', 'STANDARDIZE_NAME', 'NAMA_PERSEROAN', (df['NAMA_PERSEROAN'] != before).sum(), n,
              "Uppercase, rapikan spasi, normalisasi prefix PT/CV/Firma/Perum/UD")

    before = df['ALAMAT_PERSEROAN'].copy()
    df['ALAMAT_PERSEROAN'] = df['ALAMAT_PERSEROAN'].apply(standardize_alamat)
    audit.log('OSS', 'STANDARDIZE_ADDRESS', 'ALAMAT_PERSEROAN', (df['ALAMAT_PERSEROAN'] != before).sum(), n,
              "Title case, normalisasi singkatan (Jl., No., RT/RW, Kec., Kel.)")

    before = df['NIB'].copy()
    df['NIB'] = df['NIB'].apply(standardize_nib)
    audit.log('OSS', 'STANDARDIZE_NIB', 'NIB', (df['NIB'] != before).sum(), n,
              "Hanya digit, pad/trim ke 13 digit")

    before = df['NPWP_PERSEROAN'].copy()
    df['NPWP_PERSEROAN'] = df['NPWP_PERSEROAN'].apply(standardize_npwp)
    audit.log('OSS', 'STANDARDIZE_NPWP', 'NPWP_PERSEROAN', (df['NPWP_PERSEROAN'] != before).sum(), n,
              "Format ke XX.XXX.XXX.X-XXX.XXX (jika 15 digit)")

    df['IS_NPWP_INVALID'] = ~df['NPWP_PERSEROAN'].astype(str).str.match(NPWP_PATTERN)
    audit.log('OSS', 'FLAG_VALIDITY', 'NPWP_PERSEROAN', df['IS_NPWP_INVALID'].sum(), n,
              "Format NPWP_PERSEROAN tidak sesuai XX.XXX.XXX.X-XXX.XXX - ditandai IS_NPWP_INVALID")

    before = df['KODE_POS_PERSEROAN'].copy()
    df['KODE_POS_PERSEROAN'] = df['KODE_POS_PERSEROAN'].apply(standardize_kode_pos)
    audit.log('OSS', 'STANDARDIZE_KODEPOS', 'KODE_POS_PERSEROAN', _kode_pos_changed(before, df['KODE_POS_PERSEROAN']), n,
              "Pastikan 5 digit, selain itu dikosongkan (field opsional)")

    df['IS_INCOMPLETE'] = df[MAND_COLS_OSS].isnull().any(axis=1)
    audit.log('OSS', 'FLAG_INCOMPLETE', '+'.join(MAND_COLS_OSS), df['IS_INCOMPLETE'].sum(), n,
              "Field wajib kosong - ditandai untuk review, tidak diisi paksa")

    daerah_str = df['PERSEROAN_DAERAH_ID'].apply(lambda x: f'{int(x):02d}' if pd.notna(x) else None)
    df['IS_DAERAH_VALID'] = daerah_str.isin(PROVINSI.keys())
    audit.log('OSS', 'VALIDATE_REF', 'PERSEROAN_DAERAH_ID', (~df['IS_DAERAH_VALID']).sum(), n,
              "Kode wilayah tidak ditemukan di 34 kode referensi PROVINSI")

    tgl = pd.to_datetime(df['TGL_PERUBAHAN_NIB'], errors='coerce')
    df['IS_STALE'] = (datetime.now() - tgl).dt.days > 365
    audit.log('OSS', 'FLAG_TIMELINESS', 'TGL_PERUBAHAN_NIB', df['IS_STALE'].sum(), n,
              "IS_STALE = True jika TGL_PERUBAHAN_NIB > 1 tahun dari sekarang")

    df['IS_CLEANED'] = True
    df['CLEANSING_TIMESTAMP'] = datetime.now().isoformat()
    return df


def clean_ceisa(df_raw, audit):
    df = df_raw.copy()
    n = len(df)

    before = df['NAMA_PERUSAHAAN'].copy()
    df['NAMA_PERUSAHAAN'] = df['NAMA_PERUSAHAAN'].apply(standardize_nama)
    audit.log('CEISA', 'STANDARDIZE_NAME', 'NAMA_PERUSAHAAN', (df['NAMA_PERUSAHAAN'] != before).sum(), n,
              "Uppercase, rapikan spasi, normalisasi prefix PT/CV/Firma/Perum/UD")

    before = df['ALAMAT_PERUSAHAAN'].copy()
    df['ALAMAT_PERUSAHAAN'] = df['ALAMAT_PERUSAHAAN'].apply(standardize_alamat)
    audit.log('CEISA', 'STANDARDIZE_ADDRESS', 'ALAMAT_PERUSAHAAN', (df['ALAMAT_PERUSAHAAN'] != before).sum(), n,
              "Title case, normalisasi singkatan (Jl., No., RT/RW, Kec., Kel.)")

    before = df['NIB'].copy()
    df['NIB'] = df['NIB'].apply(standardize_nib)
    audit.log('CEISA', 'STANDARDIZE_NIB', 'NIB', (df['NIB'] != before).sum(), n,
              "Hanya digit, pad/trim ke 13 digit")

    before = df['NPWP'].copy()
    df['NPWP'] = df['NPWP'].apply(standardize_npwp)
    n_npwp_changed = (df['NPWP'] != before).sum()
    n_still_dirty = (~df['NPWP'].astype(str).str.match(NPWP_PATTERN)).sum()
    audit.log('CEISA', 'STANDARDIZE_NPWP', 'NPWP', n_npwp_changed, n,
              f"Format ke XX.XXX.XXX.X-XXX.XXX (jika 15 digit); {n_still_dirty} masih tidak baku "
              f"(anomali \"Inconsistent NPWP\" dipertahankan sesuai docs/02_business_rules.md §1)")

    df['IS_NPWP_INVALID'] = ~df['NPWP'].astype(str).str.match(NPWP_PATTERN)
    audit.log('CEISA', 'FLAG_VALIDITY', 'NPWP', df['IS_NPWP_INVALID'].sum(), n,
              "Format NPWP tidak sesuai XX.XXX.XXX.X-XXX.XXX - ditandai IS_NPWP_INVALID")

    before = df['KODE_POS'].copy()
    df['KODE_POS'] = df['KODE_POS'].apply(standardize_kode_pos)
    audit.log('CEISA', 'STANDARDIZE_KODEPOS', 'KODE_POS', _kode_pos_changed(before, df['KODE_POS']), n,
              "Pastikan 5 digit, selain itu dikosongkan (field opsional)")

    before = df['NOMOR_TELPON'].copy()
    df['NOMOR_TELPON'] = df['NOMOR_TELPON'].apply(standardize_telpon)
    audit.log('CEISA', 'STANDARDIZE_PHONE', 'NOMOR_TELPON', (df['NOMOR_TELPON'] != before).sum(), n,
              "Normalisasi ke format +62...")

    df = dedup_ceisa(df, audit)
    n = len(df)

    df['IS_INCOMPLETE'] = df[MAND_COLS_CEISA].isnull().any(axis=1)
    audit.log('CEISA', 'FLAG_INCOMPLETE', '+'.join(MAND_COLS_CEISA), df['IS_INCOMPLETE'].sum(), n,
              "Field wajib kosong - ditandai untuk review, tidak diisi paksa")

    daerah_str = df['DAERAH_ID'].apply(lambda x: f'{int(x):02d}' if pd.notna(x) else None)
    df['IS_DAERAH_VALID'] = daerah_str.isin(PROVINSI.keys())
    audit.log('CEISA', 'VALIDATE_REF', 'DAERAH_ID', (~df['IS_DAERAH_VALID']).sum(), n,
              "Kode wilayah tidak ditemukan di 34 kode referensi PROVINSI")

    tgl_sync = pd.to_datetime(df['TGL_SYNC_OSS'], errors='coerce')
    df['HIGH_SYNC_LAG'] = (datetime.now() - tgl_sync).dt.days > 30
    audit.log('CEISA', 'FLAG_TIMELINESS', 'TGL_SYNC_OSS', df['HIGH_SYNC_LAG'].sum(), n,
              "HIGH_SYNC_LAG = True jika TGL_SYNC_OSS > 30 hari dari sekarang")

    df['IS_CLEANED'] = True
    df['CLEANSING_TIMESTAMP'] = datetime.now().isoformat()
    return df


if __name__ == "__main__":
    print(f"\n{'='*65}\n TAHAP 2 - DATA CLEANSING & STANDARDIZATION\n{'='*65}")

    df_oss_raw = pd.read_csv('data/raw/oss_nib_data.csv', dtype={'NIB': str, 'NPWP_PERSEROAN': str})
    df_ceisa_raw = pd.read_csv('data/raw/ceisa_data.csv', dtype={'NIB': str, 'NPWP': str})

    audit = AuditTrail()

    print("\n[1/4] Cleansing OSS ...")
    metrics_oss_before = calculate_dq_metrics(df_oss_raw, dataset_name="OSS")
    df_oss = clean_oss(df_oss_raw, audit)
    metrics_oss_after = calculate_dq_metrics(df_oss, dataset_name="OSS")
    print(f"  OSS: {len(df_oss_raw):,} -> {len(df_oss):,} baris")
    quality_gate(df_oss, 'OSS', MAND_COLS_OSS)
    print_dq_comparison(metrics_oss_before, metrics_oss_after, 'OSS')

    print("\n[2/4] Cleansing CEISA ...")
    metrics_ceisa_before = calculate_dq_metrics(df_ceisa_raw, dataset_name="CEISA")
    df_ceisa = clean_ceisa(df_ceisa_raw, audit)
    metrics_ceisa_after = calculate_dq_metrics(df_ceisa, dataset_name="CEISA")
    print(f"  CEISA: {len(df_ceisa_raw):,} -> {len(df_ceisa):,} baris (dedup data mart)")
    quality_gate(df_ceisa, 'CEISA', MAND_COLS_CEISA)
    print_dq_comparison(metrics_ceisa_before, metrics_ceisa_after, 'CEISA')

    print("\n[3/4] Membentuk dataset_clean.csv (union OSS + CEISA) ...")
    df_clean = pd.concat(
        [df_oss.assign(SOURCE='OSS'), df_ceisa.assign(SOURCE='CEISA')],
        ignore_index=True, sort=False,
    )
    print(f"  dataset_clean.csv: {len(df_clean):,} baris, {df_clean.shape[1]} kolom")

    print("\n[4/4] Menyimpan output ...")
    df_oss.to_csv('data/processed/oss_cleaned.csv', index=False)
    df_ceisa.to_csv('data/processed/ceisa_cleaned.csv', index=False)
    df_clean.to_csv('data/processed/dataset_clean.csv', index=False)
    audit.to_dataframe().to_csv('reports/audit_trail.csv', index=False)
    print("  - data/processed/oss_cleaned.csv")
    print("  - data/processed/ceisa_cleaned.csv")
    print("  - data/processed/dataset_clean.csv")
    print("  - reports/audit_trail.csv")

    print("\n✅ Tahap 2 - Data Cleansing & Standardization selesai.")
