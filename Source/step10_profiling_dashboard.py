# [TAHAP 6] YDATA PROFILING DASHBOARD
# Berdasarkan: docs/tahapan/tahap6_profiling_dashboard.md
#
# Profiling ulang terhadap Golden Record (after MDM) menggunakan ydata_profiling,
# lalu membandingkan ringkasan profiling_before (OSS+CEISA) vs profiling_after
# (Golden Record), ditutup dengan insight bisnis & rekomendasi data governance.

import pandas as pd
from ydata_profiling import ProfileReport

from Source.step05_profiling import (
    NIB_PATTERN, NPWP_PATTERN, KODE_POS_PATTERN, _to_digit_str, YDATA_CORRELATIONS,
)

DUMMY_NIB = '0' * 13  # NIB dummy/kosong - sama dengan Source/step07_matching.py


def format_validity_pct(df, nib_col, npwp_col, kp_col):
    """Hitung % valid format untuk NIB, NPWP, dan KODE_POS (dari yang terisi)."""
    nib_valid = df[nib_col].astype(str).str.match(NIB_PATTERN).mean() * 100
    npwp_valid = df[npwp_col].astype(str).str.match(NPWP_PATTERN).mean() * 100

    kp_series = _to_digit_str(df[kp_col])
    kp_filled = kp_series.dropna()
    kp_valid = kp_filled.str.match(KODE_POS_PATTERN).mean() * 100 if len(kp_filled) else 0.0

    return nib_valid, npwp_valid, kp_valid


if __name__ == "__main__":
    df_oss = pd.read_csv('data/raw/oss_nib_data.csv')
    df_ceisa = pd.read_csv('data/raw/ceisa_data.csv')
    # NIB & NPWP dipaksa string agar leading zero (mis. NIB dummy "0000000000000")
    # tidak hilang akibat auto-infer ke int64 (lihat Source/step09_quality_monitoring.py)
    df_golden = pd.read_csv('data/golden/golden_record.csv', dtype={'NIB': str, 'NPWP': str})

    # 1-2. ydata_profiling report untuk Golden Record
    print(f"\n{'='*65}\n YDATA PROFILING REPORT — GOLDEN RECORD (AFTER MDM)\n{'='*65}")
    print("Membuat ydata_profiling report untuk Golden Record -> reports/profiling_after.html ...")
    profile = ProfileReport(
        df_golden,
        title='Data Profiling Report — Golden Record (After MDM)',
        explorative=True,
        correlations=YDATA_CORRELATIONS,
        interactions={"continuous": False},
    )
    profile.to_file('reports/profiling_after.html')
    print("Report disimpan: reports/profiling_after.html")

    # 3. Perbandingan profiling_before vs profiling_after
    print(f"\n{'='*65}\n PERBANDINGAN: BEFORE (OSS + CEISA) vs AFTER (GOLDEN RECORD)\n{'='*65}")

    n_oss, n_ceisa, n_golden = len(df_oss), len(df_ceisa), len(df_golden)
    n_before = n_oss + n_ceisa
    print("\n[Jumlah Record]")
    print(f"  OSS    (before) : {n_oss:,}")
    print(f"  CEISA  (before) : {n_ceisa:,}")
    print(f"  Total  (before) : {n_before:,}")
    print(f"  Golden (after)  : {n_golden:,}")
    print(f"  Pengurangan akibat dedup/matching: {n_before - n_golden:,} baris "
          f"({(1 - n_golden / n_before) * 100:.2f}%)")

    # Missing value % - field wajib (NIB, NPWP, NAMA, STATUS_NIB)
    mand_oss = ['NIB', 'NPWP_PERSEROAN', 'NAMA_PERSEROAN', 'STATUS_NIB']
    mand_ceisa = ['NIB', 'NPWP', 'NAMA_PERUSAHAAN', 'STATUS_NIB']
    mand_golden = ['NIB', 'NPWP', 'NAMA', 'STATUS_NIB']

    miss_oss = df_oss[mand_oss].isnull().mean().mean() * 100
    miss_ceisa = df_ceisa[mand_ceisa].isnull().mean().mean() * 100
    miss_golden = df_golden[mand_golden].isnull().mean().mean() * 100

    print("\n[Missing Value % - Field Wajib (NIB, NPWP, NAMA, STATUS_NIB)]")
    print(f"  OSS    (before) : {miss_oss:.2f}%")
    print(f"  CEISA  (before) : {miss_ceisa:.2f}%")
    print(f"  Golden (after)  : {miss_golden:.2f}%")

    # Format validity %
    nib_oss, npwp_oss, kp_oss = format_validity_pct(df_oss, 'NIB', 'NPWP_PERSEROAN', 'KODE_POS_PERSEROAN')
    nib_ceisa, npwp_ceisa, kp_ceisa = format_validity_pct(df_ceisa, 'NIB', 'NPWP', 'KODE_POS')
    nib_golden, npwp_golden, kp_golden = format_validity_pct(df_golden, 'NIB', 'NPWP', 'KODE_POS')

    print("\n[Format Validity %]")
    print(f"  {'Field':<22}{'OSS':>10}{'CEISA':>10}{'Golden':>10}")
    print(f"  {'NIB (13 digit)':<22}{nib_oss:>9.2f}%{nib_ceisa:>9.2f}%{nib_golden:>9.2f}%")
    print(f"  {'NPWP (format baku)':<22}{npwp_oss:>9.2f}%{npwp_ceisa:>9.2f}%{npwp_golden:>9.2f}%")
    print(f"  {'KODE_POS (5 digit)':<22}{kp_oss:>9.2f}%{kp_ceisa:>9.2f}%{kp_golden:>9.2f}%")

    # Duplikasi NIB
    dup_oss = df_oss['NIB'].duplicated().sum()
    dup_ceisa = df_ceisa['NIB'].duplicated().sum()
    dup_golden_real = df_golden[df_golden['NIB'].astype(str) != DUMMY_NIB]['NIB'].duplicated().sum()

    print("\n[Duplikasi NIB]")
    print(f"  OSS    (before) : {dup_oss:,} baris duplikat dari {n_oss:,} ({dup_oss / n_oss * 100:.2f}%)")
    print(f"  CEISA  (before) : {dup_ceisa:,} baris duplikat dari {n_ceisa:,} ({dup_ceisa / n_ceisa * 100:.2f}%) "
          f"(data mart, expected)")
    print(f"  Golden (after)  : {dup_golden_real:,} baris duplikat (NIB valid non-dummy) dari {n_golden:,} "
          f"({dup_golden_real / n_golden * 100:.2f}%)")

    # 4. Insight bisnis & rekomendasi data governance
    n_dummy_nib = (df_golden['NIB'].astype(str) == DUMMY_NIB).sum()
    n_out_of_sync = int(df_golden['IS_OUT_OF_SYNC'].sum()) if 'IS_OUT_OF_SYNC' in df_golden else 0
    n_logical_conflict = int(df_golden['IS_LOGICAL_CONFLICT_NIPER'].sum()) if 'IS_LOGICAL_CONFLICT_NIPER' in df_golden else 0
    n_high_sync_lag = int(df_golden['HIGH_SYNC_LAG'].apply(lambda x: bool(x) if pd.notna(x) else False).sum()) \
        if 'HIGH_SYNC_LAG' in df_golden else 0

    print(f"\n{'='*65}\n INSIGHT BISNIS & REKOMENDASI DATA GOVERNANCE\n{'='*65}")
    print(f"""
1. Konsolidasi data berhasil mengurangi {n_before - n_golden:,} baris ({(1 - n_golden / n_before) * 100:.1f}%)
   dari total record OSS+CEISA menjadi {n_golden:,} Golden Record (Single Importer/Exporter View),
   terutama berkat dedup snapshot CEISA dan exact/fuzzy matching NIB & NPWP (Tahap 3).

2. Uniqueness NIB meningkat signifikan: dari {(1 - dup_oss / n_oss) * 100:.2f}% (OSS) /
   {(1 - dup_ceisa / n_ceisa) * 100:.2f}% (CEISA) menjadi mendekati 100% di Golden Record
   (di luar NIB dummy/invalid yang sengaja dipertahankan sebagai catatan kualitas data).

3. Risiko kualitas data yang masih perlu ditindaklanjuti meski sudah ada Golden Record:
   - {n_dummy_nib:,} record memiliki NIB dummy/tidak valid ('{DUMMY_NIB}') -> perlu verifikasi ulang ke OSS.
   - {n_out_of_sync:,} record berstatus 'Sync Conflict' (STATUS_NIB OSS vs CEISA berbeda, IS_OUT_OF_SYNC=True).
   - {n_logical_conflict:,} record memiliki 'Logical Conflict' antara FLAG_EKSPOR dan NIPER.
   - {n_high_sync_lag:,} record memiliki HIGH_SYNC_LAG (CEISA belum sinkron >30 hari dari OSS).

4. Rekomendasi implementasi Data Governance & MDM:
   - Terapkan validasi format NIB/NPWP/KODE_POS di titik input (OSS & CEISA) agar anomali
     format tidak terbawa ke data mart/operasional.
   - Jadikan OSS sebagai System of Record untuk legalitas (NIB, status badan hukum) dan
     terapkan SLA sinkronisasi CEISA <30 hari untuk menekan HIGH_SYNC_LAG.
   - Bangun proses rekonsiliasi berkala (mis. bulanan) untuk menyelesaikan Sync Conflict
     dan Logical Conflict (FLAG_EKSPOR vs NIPER) yang terdeteksi di Golden Record.
   - Jadwalkan re-running pipeline profiling -> cleansing -> matching -> golden record ->
     DQ monitoring secara periodik agar dq_scorecard.csv selalu mencerminkan kondisi terkini.
""")

    print("✅ Tahap 6 - YData Profiling Dashboard selesai.")
