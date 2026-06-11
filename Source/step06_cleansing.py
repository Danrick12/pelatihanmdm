# [LAB 3] DATA CLEANSING & STANDARDIZATION (TAHAP 2)
# Berdasarkan: docs/tahapan/tahap2_cleansing_standardization.md & docs/02_business_rules.md

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import re
import os
from datetime import datetime
from Source.step02_reference import PROVINSI, STATUS_NIB_POOL

# Field wajib (dimensi Kelengkapan, docs/02_business_rules.md §1)
MANDATORY_OSS = ['NIB', 'NPWP_PERSEROAN', 'NAMA_PERSEROAN', 'STATUS_NIB']
MANDATORY_CEISA = ['NIB', 'NPWP', 'NAMA_PERUSAHAAN', 'STATUS_NIB']

PREFIX_BADAN_USAHA = ['PT', 'CV', 'FIRMA', 'PERUM', 'UD']
NPWP_PATTERN = r'^\d{2}\.\d{3}\.\d{3}\.\d{1}-\d{3}\.\d{3}$'


class AuditTrail:
    """Mencatat operasi cleansing: timestamp, operation, field, n_affected, pct_affected, description."""

    def __init__(self, dataset_name):
        self.dataset_name = dataset_name
        self.entries = []

    def log(self, operation, field, n_affected, n_total, description):
        pct = round(n_affected / n_total * 100, 2) if n_total else 0.0
        self.entries.append({
            'dataset': self.dataset_name,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'operation': operation,
            'field': field,
            'n_affected': n_affected,
            'pct_affected': pct,
            'description': description,
        })
        print(f"   [{self.dataset_name}] {operation:<16} {field:<22} -> {n_affected:>5} records ({pct}%)")


# --- FUNGSI STANDARDISASI (tahap2 langkah 2-4) ---

def standardize_name(name):
    """Uppercase, rapikan spasi & karakter aneh, normalisasi prefix badan usaha (PT/CV/Firma/Perum/UD)"""
    if pd.isna(name):
        return name
    s = re.sub(r'\s+', ' ', str(name).upper().strip())
    s = re.sub(r"[^A-Z0-9\s.,'\-()]", '', s)
    for prefix in PREFIX_BADAN_USAHA:
        s = re.sub(rf'^{prefix}\.?\s+', f'{prefix} ', s)
    return s


def standardize_address(address):
    """Title case + normalisasi singkatan alamat umum (Jl., No., RT/RW, Kec., Kel.)"""
    if pd.isna(address):
        return address
    s = re.sub(r'\s+', ' ', str(address).strip()).title()
    abbrevs = {
        r'\bJl\.?\b': 'Jl.', r'\bNo\.?\b': 'No.',
        r'\bRt\.?\b': 'RT', r'\bRw\.?\b': 'RW',
        r'\bKec\.?\b': 'Kec.', r'\bKel\.?\b': 'Kel.',
    }
    for pattern, repl in abbrevs.items():
        s = re.sub(pattern, repl, s, flags=re.IGNORECASE)
    return s


def standardize_nib(nib):
    """Sisakan hanya digit, lalu pad/trim ke 13 digit (docs/02_business_rules.md §4)"""
    digits = re.sub(r'\D', '', str(nib))
    return digits.zfill(13)[:13]


def standardize_npwp(npwp):
    """Format ke baku XX.XXX.XXX.X-XXX.XXX jika ditemukan 15 digit, selain itu kembalikan apa adanya (untuk audit)"""
    if pd.isna(npwp) or str(npwp).strip() == "":
        return npwp
    digits = re.sub(r'\D', '', str(npwp))
    if len(digits) == 15:
        return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}.{digits[8]}-{digits[9:12]}.{digits[12:]}"
    return npwp


def standardize_kode_pos(kode_pos):
    """Pastikan kode pos 5 digit; selain itu dikosongkan (NaN)"""
    if pd.isna(kode_pos) or str(kode_pos).strip() == "":
        return np.nan
    digits = re.sub(r'\D', '', str(kode_pos))
    return digits.zfill(5) if 0 < len(digits) <= 5 else np.nan


def standardize_phone(phone):
    """Normalisasi nomor telepon ke format +62..."""
    if pd.isna(phone) or str(phone).strip() == "":
        return phone
    digits = re.sub(r'\D', '', str(phone))
    if digits.startswith('0'):
        digits = '62' + digits[1:]
    elif not digits.startswith('62'):
        digits = '62' + digits
    return '+' + digits


# --- FUNGSI BANTUAN: MISSING VALUE & VALIDASI REFERENSIAL (tahap2 langkah 6-7) ---

def flag_missing_mandatory(df, mandatory_cols, audit):
    """Field wajib kosong -> ditandai IS_INCOMPLETE, tidak diisi paksa (dicatat di audit trail)"""
    df['IS_INCOMPLETE'] = df[mandatory_cols].isnull().any(axis=1)
    n_incomplete = int(df['IS_INCOMPLETE'].sum())
    audit.log('FLAG_INCOMPLETE', '+'.join(mandatory_cols), n_incomplete, len(df),
              'Field wajib kosong - ditandai untuk review, tidak diisi paksa')
    return df


def validate_referential(df, daerah_col, audit):
    """Validasi kode wilayah terhadap tabel referensi PROVINSI -> kolom IS_DAERAH_VALID"""
    df['IS_DAERAH_VALID'] = df[daerah_col].astype(str).isin(PROVINSI.keys())
    n_invalid = int((~df['IS_DAERAH_VALID']).sum())
    audit.log('VALIDATE_REF', daerah_col, n_invalid, len(df),
              f'Kode wilayah tidak ditemukan di {len(PROVINSI)} kode referensi PROVINSI')
    return df


def flag_npwp_validity(df, npwp_col, audit):
    """Tandai NPWP yang tidak sesuai format baku XX.XXX.XXX.X-XXX.XXX -> IS_NPWP_INVALID
    (dimensi Validitas; quality gate memastikan NPWP invalid tidak lolos tanpa flag)"""
    df['IS_NPWP_INVALID'] = ~df[npwp_col].astype(str).str.match(NPWP_PATTERN)
    n_invalid = int(df['IS_NPWP_INVALID'].sum())
    audit.log('FLAG_VALIDITY', npwp_col, n_invalid, len(df),
              f'Format {npwp_col} tidak sesuai XX.XXX.XXX.X-XXX.XXX - ditandai IS_NPWP_INVALID')
    return df


# --- CLEANSING OSS (Lab 3 - Part A) ---

def clean_oss_master(df):
    """
    Cleansing & standardisasi dataset OSS sesuai tahap2_cleansing_standardization.md.
    Catatan: tidak melakukan dedup NIB di sini - sisa anomali "Duplicate Entry" sengaja
    dibawa ke Tahap 4 (golden record langkah 8), bukan dibuang di Tahap 2.
    """
    df_clean = df.copy()
    n = len(df_clean)
    audit = AuditTrail('OSS')
    print(f"Memulai Cleansing OSS ({n} records)...")

    # Standardisasi nama
    before = df_clean['NAMA_PERSEROAN'].copy()
    df_clean['NAMA_PERSEROAN'] = df_clean['NAMA_PERSEROAN'].apply(standardize_name)
    df_clean['NAMA_SINGKATAN'] = df_clean['NAMA_SINGKATAN'].apply(standardize_name)
    audit.log('STANDARDIZE_NAME', 'NAMA_PERSEROAN', int((before != df_clean['NAMA_PERSEROAN']).sum()), n,
              'Uppercase, rapikan spasi, normalisasi prefix PT/CV/Firma/Perum/UD')

    # Standardisasi alamat
    before = df_clean['ALAMAT_PERSEROAN'].copy()
    df_clean['ALAMAT_PERSEROAN'] = df_clean['ALAMAT_PERSEROAN'].apply(standardize_address)
    audit.log('STANDARDIZE_ADDRESS', 'ALAMAT_PERSEROAN', int((before != df_clean['ALAMAT_PERSEROAN']).sum()), n,
              'Title case, normalisasi singkatan (Jl., No., RT/RW, Kec., Kel.)')

    # Standardisasi identifier: NIB, NPWP, KODE_POS
    before = df_clean['NIB'].astype(str).copy()
    df_clean['NIB'] = df_clean['NIB'].apply(standardize_nib)
    audit.log('STANDARDIZE_NIB', 'NIB', int((before != df_clean['NIB']).sum()), n,
              'Hanya digit, pad/trim ke 13 digit')

    before = df_clean['NPWP_PERSEROAN'].copy()
    df_clean['NPWP_PERSEROAN'] = df_clean['NPWP_PERSEROAN'].apply(standardize_npwp)
    audit.log('STANDARDIZE_NPWP', 'NPWP_PERSEROAN', int((before != df_clean['NPWP_PERSEROAN']).sum()), n,
              'Format ke XX.XXX.XXX.X-XXX.XXX (jika 15 digit)')
    df_clean = flag_npwp_validity(df_clean, 'NPWP_PERSEROAN', audit)

    before = df_clean['KODE_POS_PERSEROAN'].copy()
    df_clean['KODE_POS_PERSEROAN'] = df_clean['KODE_POS_PERSEROAN'].apply(standardize_kode_pos)
    audit.log('STANDARDIZE_KODEPOS', 'KODE_POS_PERSEROAN', int((before != df_clean['KODE_POS_PERSEROAN']).sum()), n,
              'Pastikan 5 digit, selain itu dikosongkan')

    # Penanganan missing value: field wajib -> flag, field opsional -> biarkan null
    df_clean = flag_missing_mandatory(df_clean, MANDATORY_OSS, audit)

    # Validasi referensial kode wilayah
    df_clean = validate_referential(df_clean, 'PERSEROAN_DAERAH_ID', audit)

    # Ketepatan Waktu: IS_STALE (TGL_PERUBAHAN_NIB > 1 tahun) - dibawa ke Tahap 4 (tidak dihitung ulang)
    tgl = pd.to_datetime(df_clean['TGL_PERUBAHAN_NIB'], errors='coerce')
    df_clean['IS_STALE'] = (datetime.now() - tgl).dt.days > 365
    audit.log('FLAG_TIMELINESS', 'TGL_PERUBAHAN_NIB', int(df_clean['IS_STALE'].sum()), n,
              'IS_STALE = True jika TGL_PERUBAHAN_NIB > 1 tahun dari sekarang')

    # Audit metadata
    df_clean['IS_CLEANED'] = True
    df_clean['CLEANSING_TIMESTAMP'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    print(f"Cleansing OSS selesai. {int(df_clean['IS_INCOMPLETE'].sum())} record ditandai IS_INCOMPLETE.")
    return df_clean, audit


# --- CLEANSING CEISA (Lab 3 - Part B) ---

def clean_ceisa_data(df):
    """
    Cleansing, standardisasi, & data mart dedup dataset CEISA sesuai
    tahap2_cleansing_standardization.md. Hasil akhir: 1 baris per NIB
    (snapshot dengan TGL_SYNC_OSS terbaru yang dipertahankan).
    """
    df_clean = df.copy()
    n = len(df_clean)
    audit = AuditTrail('CEISA')
    print(f"Memulai Cleansing CEISA ({n} records)...")

    # Standardisasi nama
    before = df_clean['NAMA_PERUSAHAAN'].copy()
    df_clean['NAMA_PERUSAHAAN'] = df_clean['NAMA_PERUSAHAAN'].apply(standardize_name)
    audit.log('STANDARDIZE_NAME', 'NAMA_PERUSAHAAN', int((before != df_clean['NAMA_PERUSAHAAN']).sum()), n,
              'Uppercase, rapikan spasi, normalisasi prefix PT/CV/Firma/Perum/UD')

    # Standardisasi alamat
    before = df_clean['ALAMAT_PERUSAHAAN'].copy()
    df_clean['ALAMAT_PERUSAHAAN'] = df_clean['ALAMAT_PERUSAHAAN'].apply(standardize_address)
    audit.log('STANDARDIZE_ADDRESS', 'ALAMAT_PERUSAHAAN', int((before != df_clean['ALAMAT_PERUSAHAAN']).sum()), n,
              'Title case, normalisasi singkatan (Jl., No., RT/RW, Kec., Kel.)')

    # Standardisasi identifier: NIB, NPWP, KODE_POS, NOMOR_TELPON
    before = df_clean['NIB'].astype(str).copy()
    df_clean['NIB'] = df_clean['NIB'].apply(standardize_nib)
    audit.log('STANDARDIZE_NIB', 'NIB', int((before != df_clean['NIB']).sum()), n,
              'Hanya digit, pad/trim ke 13 digit')

    before = df_clean['NPWP'].copy()
    df_clean['NPWP'] = df_clean['NPWP'].apply(standardize_npwp)
    n_npwp_dirty = int((~df_clean['NPWP'].astype(str).str.match(NPWP_PATTERN)).sum())
    audit.log('STANDARDIZE_NPWP', 'NPWP', int((before != df_clean['NPWP']).sum()), n,
              f'Format ke XX.XXX.XXX.X-XXX.XXX (jika 15 digit); {n_npwp_dirty} masih tidak baku '
              f'(anomali "Inconsistent NPWP" dipertahankan sesuai docs/02_business_rules.md §1)')
    df_clean = flag_npwp_validity(df_clean, 'NPWP', audit)

    before = df_clean['KODE_POS'].copy()
    df_clean['KODE_POS'] = df_clean['KODE_POS'].apply(standardize_kode_pos)
    audit.log('STANDARDIZE_KODEPOS', 'KODE_POS', int((before != df_clean['KODE_POS']).sum()), n,
              'Pastikan 5 digit, selain itu dikosongkan')

    before = df_clean['NOMOR_TELPON'].copy()
    df_clean['NOMOR_TELPON'] = df_clean['NOMOR_TELPON'].apply(standardize_phone)
    audit.log('STANDARDIZE_PHONE', 'NOMOR_TELPON', int((before != df_clean['NOMOR_TELPON']).sum()), n,
              'Normalisasi ke format +62...')

    # CEISA Data Mart Dedup: per NIB ambil snapshot dengan TGL_SYNC_OSS terbaru
    df_clean['TGL_SYNC_OSS'] = pd.to_datetime(df_clean['TGL_SYNC_OSS'], errors='coerce')
    df_clean = df_clean.sort_values('TGL_SYNC_OSS', ascending=False)
    n_multi_snapshot = int((df_clean.groupby('NIB').size() > 1).sum())
    n_before_dedup = len(df_clean)
    df_clean = df_clean.drop_duplicates(subset=['NIB'], keep='first')
    n_dropped = n_before_dedup - len(df_clean)
    audit.log('DEDUP_SNAPSHOT', 'NIB', n_dropped, n_before_dedup,
              f'{n_multi_snapshot} NIB punya >1 snapshot data mart - disisakan baris TGL_SYNC_OSS terbaru')
    df_clean['TGL_SYNC_OSS'] = df_clean['TGL_SYNC_OSS'].dt.strftime('%Y-%m-%d')
    n = len(df_clean)

    # Penanganan missing value: field wajib -> flag, field opsional -> biarkan null
    df_clean = flag_missing_mandatory(df_clean, MANDATORY_CEISA, audit)

    # Validasi referensial kode wilayah
    df_clean = validate_referential(df_clean, 'DAERAH_ID', audit)

    # Ketepatan Waktu: HIGH_SYNC_LAG (TGL_SYNC_OSS > 30 hari) - dibawa ke Tahap 4 (tidak dihitung ulang)
    tgl_sync = pd.to_datetime(df_clean['TGL_SYNC_OSS'], errors='coerce')
    df_clean['HIGH_SYNC_LAG'] = (datetime.now() - tgl_sync).dt.days > 30
    audit.log('FLAG_TIMELINESS', 'TGL_SYNC_OSS', int(df_clean['HIGH_SYNC_LAG'].sum()), n,
              'HIGH_SYNC_LAG = True jika TGL_SYNC_OSS > 30 hari dari sekarang')

    # Audit metadata
    df_clean['IS_CLEANED'] = True
    df_clean['CLEANSING_TIMESTAMP'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    print(f"Cleansing CEISA selesai. {n_dropped} snapshot lama dibuang -> {n} records (1 baris/NIB).")
    return df_clean, audit


# --- QUALITY GATE (tahap2 langkah 8) ---

class QualityGate:
    """Runner pemeriksaan otomatis sebelum export. Setiap check menghasilkan
    nilai (persen) yang dibandingkan terhadap threshold minimum."""

    def __init__(self, df, dataset_name):
        self.df = df
        self.dataset_name = dataset_name
        self.results = []
        self.all_pass = True

    def check(self, gate_name, condition_fn, threshold, description):
        try:
            value = condition_fn(self.df)
            passed = value >= threshold
            status = 'PASS' if passed else 'FAIL'
        except Exception as e:
            value = -1
            passed = False
            status = f'ERROR: {e}'
        if not passed:
            self.all_pass = False
        self.results.append({
            'dataset': self.dataset_name,
            'gate': gate_name,
            'description': description,
            'value': round(value, 2) if isinstance(value, float) else value,
            'threshold': threshold,
            'status': status,
        })
        val_str = f'{value:.2f}' if isinstance(value, float) else str(value)
        print(f"   {status:<6} [{self.dataset_name}] {gate_name:<18} {description:<58} (nilai: {val_str}, min: {threshold})")


def run_quality_gates(df_oss, df_ceisa):
    """Bangun & jalankan quality gate (tahap2 langkah 8) untuk OSS & CEISA.
    Memastikan tidak ada NIB/NPWP invalid format yang lolos tanpa flag,
    field wajib lengkap (atau ditandai IS_INCOMPLETE), dan kode wilayah valid."""
    print("\nQuality Gate:")

    qg_oss = QualityGate(df_oss, 'OSS')
    qg_oss.check('NIB_FORMAT', lambda d: d['NIB'].astype(str).str.match(r'^\d{13}$').mean() * 100,
                  100, 'NIB 13 digit numerik')
    qg_oss.check('NPWP_FORMAT', lambda d: (~d['IS_NPWP_INVALID']).mean() * 100,
                  100, 'NPWP_PERSEROAN format baku XX.XXX.XXX.X-XXX.XXX')
    qg_oss.check('STATUS_NIB_VALID', lambda d: d['STATUS_NIB'].isin(STATUS_NIB_POOL).mean() * 100,
                  100, 'STATUS_NIB hanya nilai valid (AKTIF/DIBEKUKAN/DICABUT)')
    qg_oss.check('MANDATORY_COMPLETE', lambda d: (~d['IS_INCOMPLETE']).mean() * 100,
                  100, 'Field wajib (NIB/NPWP/NAMA/STATUS_NIB) terisi')
    qg_oss.check('DAERAH_VALID', lambda d: d['IS_DAERAH_VALID'].mean() * 100,
                  100, 'PERSEROAN_DAERAH_ID terdaftar di referensi PROVINSI')

    qg_ceisa = QualityGate(df_ceisa, 'CEISA')
    qg_ceisa.check('NIB_FORMAT', lambda d: d['NIB'].astype(str).str.match(r'^\d{13}$').mean() * 100,
                    100, 'NIB 13 digit numerik')
    qg_ceisa.check('NIB_UNIQUE', lambda d: (d['NIB'].nunique() / len(d)) * 100,
                    100, '1 baris per NIB (data mart sudah dedup)')
    qg_ceisa.check('NPWP_FORMAT', lambda d: (~d['IS_NPWP_INVALID']).mean() * 100,
                    75, 'NPWP format baku (anomali "Inconsistent NPWP" ditoleransi & ditandai IS_NPWP_INVALID)')
    qg_ceisa.check('STATUS_NIB_VALID', lambda d: d['STATUS_NIB'].isin(STATUS_NIB_POOL).mean() * 100,
                    100, 'STATUS_NIB hanya nilai valid (AKTIF/DIBEKUKAN/DICABUT)')
    qg_ceisa.check('MANDATORY_COMPLETE', lambda d: (~d['IS_INCOMPLETE']).mean() * 100,
                    100, 'Field wajib (NIB/NPWP/NAMA/STATUS_NIB) terisi')
    qg_ceisa.check('DAERAH_VALID', lambda d: d['IS_DAERAH_VALID'].mean() * 100,
                    100, 'DAERAH_ID terdaftar di referensi PROVINSI')

    all_pass = qg_oss.all_pass and qg_ceisa.all_pass
    verdict = 'SEMUA GATE PASS - Dataset siap diekspor' if all_pass else 'ADA GATE YANG GAGAL - Periksa sebelum export'
    print(f"   -> {verdict}")

    report_df = pd.DataFrame(qg_oss.results + qg_ceisa.results)
    return all_pass, report_df


# --- EXPORT RECORD UNTUK REVIEW MANUAL (tahap2 langkah 6-8) ---

def export_flagged_records(df_oss, df_ceisa):
    """Kumpulkan record yang ditandai IS_INCOMPLETE / IS_DAERAH_VALID=False / IS_NPWP_INVALID
    untuk review manual -> reports/flagged_for_review.csv"""
    flagged = []
    sources = [
        ('OSS', df_oss, 'NPWP_PERSEROAN', 'PERSEROAN_DAERAH_ID', 'NAMA_PERSEROAN'),
        ('CEISA', df_ceisa, 'NPWP', 'DAERAH_ID', 'NAMA_PERUSAHAAN'),
    ]
    for source_name, df, npwp_col, daerah_col, nama_col in sources:
        mask = df['IS_INCOMPLETE'] | (~df['IS_DAERAH_VALID']) | df['IS_NPWP_INVALID']
        cols = ['NIB', nama_col, npwp_col, daerah_col, 'STATUS_NIB',
                'IS_INCOMPLETE', 'IS_DAERAH_VALID', 'IS_NPWP_INVALID']
        sub = df.loc[mask, cols].copy()
        sub = sub.rename(columns={nama_col: 'NAMA', npwp_col: 'NPWP', daerah_col: 'DAERAH_ID'})
        sub.insert(0, 'SOURCE', source_name)

        def build_reason(row):
            reasons = []
            if row['IS_INCOMPLETE']:
                reasons.append('FIELD_WAJIB_KOSONG')
            if not row['IS_DAERAH_VALID']:
                reasons.append('KODE_WILAYAH_TIDAK_VALID')
            if row['IS_NPWP_INVALID']:
                reasons.append('FORMAT_NPWP_TIDAK_BAKU')
            return '; '.join(reasons)

        sub['FLAG_REASON'] = sub.apply(build_reason, axis=1)
        flagged.append(sub)

    df_flagged = pd.concat(flagged, ignore_index=True)
    df_flagged.to_csv('reports/flagged_for_review.csv', index=False)
    return df_flagged


# --- VISUALISASI DQ SCORE BEFORE VS AFTER (tahap2 langkah 10) ---

def plot_dq_comparison(before_metrics, after_metrics, dataset_name):
    """Grouped bar (before vs after) + delta chart per dimensi DQ -> reports/dq_comparison_<nama>.png"""
    dims = list(before_metrics.keys())
    before = [before_metrics[d] for d in dims]
    after = [after_metrics[d] for d in dims]
    deltas = [a - b for a, b in zip(after, before)]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle(f'DQ Score Before vs After Cleansing - {dataset_name}', fontsize=14, fontweight='bold')

    ax1 = axes[0]
    x = np.arange(len(dims))
    w = 0.35
    ax1.bar(x - w / 2, before, w, label='Before', color='#FF7043', alpha=0.85)
    ax1.bar(x + w / 2, after, w, label='After', color='#4CAF50', alpha=0.85)
    ax1.set_xticks(x)
    ax1.set_xticklabels(dims, fontsize=9, rotation=15)
    ax1.set_ylim(0, 110)
    ax1.set_ylabel('Score (%)')
    ax1.legend()
    ax1.set_title('Skor per Dimensi')
    for i, (b, a) in enumerate(zip(before, after)):
        ax1.text(i - w / 2, b + 1, f'{b:.1f}', ha='center', fontsize=8)
        ax1.text(i + w / 2, a + 1, f'{a:.1f}', ha='center', fontsize=8, color='green', fontweight='bold')

    ax2 = axes[1]
    colors = ['#4CAF50' if d >= 0 else '#F44336' for d in deltas]
    ax2.barh(dims, deltas, color=colors, edgecolor='white')
    ax2.axvline(x=0, color='black', linewidth=0.8)
    ax2.set_xlabel('Delta Score (%)')
    ax2.set_title(f'Peningkatan per Dimensi (Total: {sum(deltas):+.2f} poin)')
    for i, d in enumerate(deltas):
        ax2.text(d + (0.5 if d >= 0 else -0.5), i, f'{d:+.2f}%',
                 va='center', ha='left' if d >= 0 else 'right', fontsize=9, fontweight='bold')

    plt.tight_layout()
    filename = f'reports/dq_comparison_{dataset_name.lower()}.png'
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"   Chart disimpan: {filename}")


if __name__ == "__main__":
    try:
        os.makedirs('data/processed', exist_ok=True)
        os.makedirs('reports', exist_ok=True)

        # 1. Load Raw
        df_oss_raw = pd.read_csv('data/raw/oss_nib_data.csv')
        df_ceisa_raw = pd.read_csv('data/raw/ceisa_data.csv')

        # 2-7. Cleansing per dataset
        df_oss_clean, audit_oss = clean_oss_master(df_oss_raw)
        df_ceisa_clean, audit_ceisa = clean_ceisa_data(df_ceisa_raw)

        # 8. Quality Gate
        gate_pass, gate_report = run_quality_gates(df_oss_clean, df_ceisa_clean)
        gate_report.to_csv('reports/quality_gate_report.csv', index=False)

        # 9. Export oss_cleaned, ceisa_cleaned, dataset_clean (union + SOURCE), audit_trail
        df_oss_clean.to_csv('data/processed/oss_cleaned.csv', index=False)
        df_ceisa_clean.to_csv('data/processed/ceisa_cleaned.csv', index=False)

        df_dataset_clean = pd.concat([
            df_oss_clean.assign(SOURCE='OSS'),
            df_ceisa_clean.assign(SOURCE='CEISA'),
        ], ignore_index=True)
        df_dataset_clean.to_csv('data/processed/dataset_clean.csv', index=False)

        audit_df = pd.DataFrame(audit_oss.entries + audit_ceisa.entries)
        audit_df.to_csv('reports/audit_trail.csv', index=False)

        df_flagged = export_flagged_records(df_oss_clean, df_ceisa_clean)

        print(f"\nExport selesai:")
        print(f"   - data/processed/oss_cleaned.csv      ({len(df_oss_clean)} records)")
        print(f"   - data/processed/ceisa_cleaned.csv    ({len(df_ceisa_clean)} records)")
        print(f"   - data/processed/dataset_clean.csv    ({len(df_dataset_clean)} records)")
        print(f"   - reports/audit_trail.csv             ({len(audit_df)} entries)")
        print(f"   - reports/quality_gate_report.csv     ({len(gate_report)} checks)")
        print(f"   - reports/flagged_for_review.csv      ({len(df_flagged)} records)")

        # 10. Perbandingan DQ score before vs after
        from Source.step05_profiling import calculate_dq_metrics
        print("\n" + "=" * 50)
        print("  DQ SCORE: BEFORE (raw) vs AFTER (cleaned)")
        print("=" * 50)
        for name, before_df, after_df in [("OSS", df_oss_raw, df_oss_clean), ("CEISA", df_ceisa_raw, df_ceisa_clean)]:
            before_metrics = calculate_dq_metrics(before_df, name)
            after_metrics = calculate_dq_metrics(after_df, name)
            print(f"\n{name}:")
            for dim in before_metrics:
                print(f"   {dim:<18} {before_metrics[dim]:6.1f}%  ->  {after_metrics[dim]:6.1f}%")
            plot_dq_comparison(before_metrics, after_metrics, name)
        print("=" * 50)

    except FileNotFoundError as e:
        print(f"Error: {e}")
