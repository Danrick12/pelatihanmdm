# [TAHAP 1] DATA PROFILING
# Berdasarkan: docs/tahapan/tahap1_data_profiling.md & docs/02_business_rules.md §1, §4
#
# Profiling lengkap untuk OSS & CEISA (kondisi sebelum cleansing/MDM):
#   1. Dataset overview (shape, dtype, null, unique)
#   2. Statistik deskriptif (numerik & kategorik)
#   3. Missing value analysis (tabel + severity + visualisasi)
#   4. Duplicate analysis (full duplicate, duplicate by NIB, duplicate by NAMA)
#   5. Format validation (NIB, NPWP, KODE_POS, STATUS_NIB, dst.)
#   6. Baseline Data Quality Score (4 dimensi DMBOK)
#   7. Laporan ydata_profiling -> reports/profiling_before.html

import matplotlib
matplotlib.use('Agg')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import missingno as msno
import re
from datetime import datetime
from ydata_profiling import ProfileReport

from Source.step02_reference import (
    STATUS_NIB_POOL, JENIS_PERSEROAN_POOL, KATEGORI_CEISA_POOL,
)

NIB_PATTERN = re.compile(r'^\d{13}$')
NPWP_PATTERN = re.compile(r'^\d{2}\.\d{3}\.\d{3}\.\d{1}-\d{3}\.\d{3}$')
KODE_POS_PATTERN = re.compile(r'^\d{5}$')


def _to_digit_str(series):
    """KODE_POS terbaca float64 (mis. 1330.0) - konversi ke string digit tanpa '.0'
    agar leading zero yang hilang akibat tipe numerik tetap terdeteksi sebagai
    format tidak valid."""
    def conv(x):
        if pd.isna(x):
            return None
        if isinstance(x, float) and x.is_integer():
            return str(int(x))
        return str(x)
    return series.apply(conv)


# ───────────────────────── 1. DATASET OVERVIEW ─────────────────────────
def dataset_overview(df, name):
    print(f"\n{'='*65}\n 1. DATASET OVERVIEW — {name}\n{'='*65}")
    print(f"Jumlah baris : {len(df):,}")
    print(f"Jumlah kolom : {df.shape[1]}")

    overview = pd.DataFrame({
        'dtype': df.dtypes.astype(str),
        'n_null': df.isnull().sum(),
        'pct_null': (df.isnull().sum() / len(df) * 100).round(2),
        'n_unique': df.nunique(),
    })
    print("\nRingkasan kolom:")
    print(overview.to_string())
    return overview


# ───────────────────────── 2. STATISTIK DESKRIPTIF ─────────────────────────
def descriptive_stats(df, name):
    print(f"\n{'='*65}\n 2. STATISTIK DESKRIPTIF — {name}\n{'='*65}")

    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if num_cols:
        print("\n[Kolom Numerik]")
        print(df[num_cols].describe().to_string())

    print("\n[Kolom Kategorik/Enum - Top 5 Value Counts]")
    cat_cols = df.select_dtypes(include=['object']).columns.tolist()
    for col in cat_cols:
        if df[col].nunique() <= 20:
            print(f"\n{col}:")
            print(df[col].value_counts(dropna=False).head(5).to_string())


# ───────────────────────── 3. MISSING VALUE ANALYSIS ─────────────────────────
def _severity(pct):
    if pct == 0:
        return 'OK'
    if pct <= 5:
        return 'LOW'
    if pct <= 15:
        return 'MEDIUM'
    if pct <= 30:
        return 'HIGH'
    return 'CRITICAL'


def missing_value_analysis(df, name):
    print(f"\n{'='*65}\n 3. MISSING VALUE ANALYSIS — {name}\n{'='*65}")
    n = len(df)
    n_missing = df.isnull().sum()
    pct_missing = (n_missing / n * 100).round(2)

    table = pd.DataFrame({'n_missing': n_missing, 'pct_missing': pct_missing})
    table['severity'] = table['pct_missing'].apply(_severity)
    table = table[table['n_missing'] > 0].sort_values('pct_missing', ascending=False)

    if table.empty:
        print("Tidak ada missing value pada kolom apapun.")
    else:
        print(table.to_string())

    # Visualisasi: bar chart % missing + missingno matrix
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    pct_missing.sort_values(ascending=False).plot.bar(ax=axes[0], color='#F44336')
    axes[0].set_title(f'% Missing per Kolom — {name}')
    axes[0].set_ylabel('% Missing')
    axes[0].axhline(0, color='black', linewidth=0.5)

    msno.matrix(df, ax=axes[1], sparkline=False)
    axes[1].set_title(f'Missing Value Matrix — {name}')

    plt.tight_layout()
    fname = f'reports/missing_value_{name.lower()}.png'
    plt.savefig(fname, dpi=120, bbox_inches='tight')
    plt.close(fig)
    print(f'\nChart disimpan: {fname}')
    return table


# ───────────────────────── 4. DUPLICATE ANALYSIS ─────────────────────────
def duplicate_analysis(df, name, nama_col):
    print(f"\n{'='*65}\n 4. DUPLICATE ANALYSIS — {name}\n{'='*65}")
    n = len(df)

    full_dup = df.duplicated(keep=False)
    print(f"Full duplicate (semua kolom identik) : {full_dup.sum():,} baris")

    nib_dup = df['NIB'].duplicated(keep=False)
    print(f"Duplicate by NIB                     : {nib_dup.sum():,} baris "
          f"({nib_dup.sum() / n * 100:.2f}%)")

    if name == 'OSS':
        if nib_dup.sum() > 0:
            print("  -> ANOMALI: NIB seharusnya unik di OSS (lihat business rules dimensi 'Unik').")
        else:
            print("  -> OK: NIB unik di OSS, sesuai harapan (sumber legalitas/master).")
    else:
        # CEISA bersifat data mart - duplikat NIB expected, dipisah jadi:
        # - Data Mart Snapshot Duplicate: NIB sama, baris berbeda (snapshot historis)
        # - Duplicate Entry: baris benar-benar identik (anomali)
        snapshot_dup = nib_dup & ~full_dup
        print(f"  -> Data Mart Snapshot Duplicate (NIB sama, isi beda) : {snapshot_dup.sum():,} baris "
              f"(EXPECTED, lihat business rules anomali #7)")
        print(f"  -> Duplicate Entry (baris identik)                   : {full_dup.sum():,} baris "
              f"(ANOMALI, lihat business rules anomali #6)")

    nama_dup = df[nama_col].duplicated(keep=False)
    print(f"Duplicate by {nama_col:<22}: {nama_dup.sum():,} baris ({nama_dup.sum() / n * 100:.2f}%)")

    return {
        'full_duplicate': int(full_dup.sum()),
        'duplicate_by_nib': int(nib_dup.sum()),
        f'duplicate_by_{nama_col}': int(nama_dup.sum()),
    }


# ───────────────────────── 5. FORMAT VALIDATION ─────────────────────────
def format_validation(df, name):
    print(f"\n{'='*65}\n 5. FORMAT VALIDATION — {name}\n{'='*65}")
    n = len(df)
    checks = {}

    nib_valid = df['NIB'].astype(str).str.match(NIB_PATTERN).sum()
    checks['NIB (13 digit)'] = (int(nib_valid), n)

    npwp_col = 'NPWP_PERSEROAN' if name == 'OSS' else 'NPWP'
    npwp_valid = df[npwp_col].astype(str).str.match(NPWP_PATTERN).sum()
    checks[f'{npwp_col} (format XX.XXX.XXX.X-XXX.XXX)'] = (int(npwp_valid), n)

    kp_col = 'KODE_POS_PERSEROAN' if name == 'OSS' else 'KODE_POS'
    kp_series = _to_digit_str(df[kp_col])
    kp_notna = int(kp_series.notna().sum())
    kp_valid = int(kp_series.dropna().str.match(KODE_POS_PATTERN).sum())
    checks[f'{kp_col} (5 digit, dari yg terisi)'] = (kp_valid, kp_notna)

    status_valid = df['STATUS_NIB'].isin(STATUS_NIB_POOL).sum()
    checks['STATUS_NIB (enum AKTIF/DIBEKUKAN/DICABUT)'] = (int(status_valid), n)

    if name == 'OSS':
        jp_valid = df['JENIS_PERSEROAN'].isin(JENIS_PERSEROAN_POOL).sum()
        checks['JENIS_PERSEROAN (enum valid)'] = (int(jp_valid), n)
    else:
        kat_valid = df['KATEGORI'].isin(KATEGORI_CEISA_POOL).sum()
        checks['KATEGORI (enum valid)'] = (int(kat_valid), n)

    for label, (valid, total) in checks.items():
        pct = valid / total * 100 if total else 0.0
        print(f"  {label:<42}: {valid:>5,}/{total:<5,} valid ({pct:6.2f}%)")

    return checks


# ───────────────────────── 6. BASELINE DQ SCORE (4 DIMENSI DMBOK) ─────────────────────────
def calculate_dq_metrics(df, dataset_name="OSS"):
    """
    Menghitung skor kualitas data berdasarkan 4 dimensi DMBOK
    (Kelengkapan, Validitas, Unik, Ketepatan Waktu) sesuai docs/02_business_rules.md §1.
    """
    n_rows = len(df)
    results = {}

    # 1. KELENGKAPAN (Completeness) - field wajib: NIB, NPWP, NAMA, STATUS_NIB
    mand_cols = ['NIB', 'STATUS_NIB']
    mand_cols += ['NPWP_PERSEROAN', 'NAMA_PERSEROAN'] if dataset_name == "OSS" else ['NPWP', 'NAMA_PERUSAHAAN']
    comp_score = (1 - df[mand_cols].isnull().any(axis=1).sum() / n_rows) * 100
    results['Kelengkapan'] = comp_score

    # 2. VALIDITAS (Validity) - format NIB (13 digit) & NPWP (XX.XXX.XXX.X-XXX.XXX)
    v_nib = df['NIB'].astype(str).str.match(NIB_PATTERN).mean() * 100
    npwp_col = 'NPWP_PERSEROAN' if dataset_name == "OSS" else 'NPWP'
    v_npwp = df[npwp_col].astype(str).str.match(NPWP_PATTERN).mean() * 100
    results['Validitas'] = (v_nib + v_npwp) / 2

    # 3. UNIK (Uniqueness) - duplikat NIB
    uniq_score = (df['NIB'].nunique() / n_rows) * 100
    results['Unik'] = uniq_score

    # 4. KETEPATAN WAKTU (Timeliness)
    #    OSS  -> IS_STALE: TGL_PERUBAHAN_NIB > 1 tahun dari sekarang
    #    CEISA -> HIGH_SYNC_LAG: TGL_SYNC_OSS > 30 hari dari sekarang
    if dataset_name == "OSS":
        tgl = pd.to_datetime(df['TGL_PERUBAHAN_NIB'], errors='coerce')
        is_stale = (datetime.now() - tgl).dt.days > 365
        timeliness_score = (1 - is_stale.sum() / n_rows) * 100
    else:
        tgl_sync = pd.to_datetime(df['TGL_SYNC_OSS'], errors='coerce')
        high_sync_lag = (datetime.now() - tgl_sync).dt.days > 30
        timeliness_score = (1 - high_sync_lag.sum() / n_rows) * 100
    results['Ketepatan Waktu'] = timeliness_score

    return results


def generate_professional_scorecard(metrics, title_suffix="CEISA"):
    """Visualisasi Dual-Chart: Hexagon Radar & Horizontal Bar."""
    dim_names = list(metrics.keys())
    dim_scores = list(metrics.values())
    total_dq_score = np.mean(dim_scores)

    TARGET_SCORE = 80
    WARNING_SCORE = 70

    if total_dq_score >= TARGET_SCORE:
        grade, grade_color = 'A (Excellent)', '#4CAF50'
    elif total_dq_score >= WARNING_SCORE:
        grade, grade_color = 'B (Good)', '#8BC34A'
    elif total_dq_score >= 60:
        grade, grade_color = 'C (Fair)', '#FF9800'
    else:
        grade, grade_color = 'D (Poor)', '#F44336'

    fig = plt.figure(figsize=(16, 8))
    fig.suptitle(f'Data Quality Scorecard — {title_suffix} (Before MDM)', fontsize=16, fontweight='bold', y=1.05)

    # ── Chart 1: Radar Chart (Hexagon) ──
    angles = np.linspace(0, 2 * np.pi, len(dim_names), endpoint=False).tolist()
    dim_scores_polar = dim_scores + [dim_scores[0]]
    angles += [angles[0]]

    ax1 = plt.subplot(121, polar=True)
    ax1.set_theta_offset(np.pi / 2)
    ax1.set_theta_direction(-1)

    ax1.plot(angles, dim_scores_polar, 'o-', linewidth=3, color='#2196F3', markersize=8)
    ax1.fill(angles, dim_scores_polar, alpha=0.3, color='#2196F3')
    ax1.plot(angles, [TARGET_SCORE] * len(angles), '--', color='red', alpha=0.6, label=f'Target {TARGET_SCORE}%')

    ax1.set_xticks(angles[:-1])
    ax1.set_xticklabels(dim_names, fontsize=10, fontweight='bold')
    ax1.set_ylim(0, 100)
    ax1.set_yticks([20, 40, 60, 80, 100])
    ax1.set_yticklabels(['20', '40', '60', '80', '100%'], fontsize=8)
    ax1.set_title('DQ Score Dimensions (DMBOK)', fontweight='bold', pad=30)
    ax1.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1), fontsize=9)

    for angle, score in zip(angles[:-1], dim_scores):
        ax1.annotate(f'{score:.1f}%', xy=(angle, score), fontsize=9, ha='center',
                      xytext=(0, 10), textcoords='offset points', color='white',
                      fontweight='bold', bbox=dict(boxstyle='round,pad=0.3', fc='#1565C0', alpha=0.8))

    # ── Chart 2: Horizontal Bar Chart ──
    ax2 = plt.subplot(122)
    y_pos = np.arange(len(dim_names))
    colors2 = [grade_color if s >= TARGET_SCORE else '#FF9800' if s >= WARNING_SCORE else '#F44336' for s in dim_scores]

    bars2 = ax2.barh(y_pos, dim_scores, color=colors2, edgecolor='white', height=0.6)
    ax2.axvline(x=TARGET_SCORE, color='red', linestyle='--', linewidth=2, label=f'Target {TARGET_SCORE}%')

    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(dim_names, fontsize=10, fontweight='bold')
    ax2.set_xlim(0, 105)
    ax2.set_xlabel('Score (%)')
    ax2.set_title(f'DQ Score vs Target\n(Avg Score: {total_dq_score:.1f}/100 | Grade: {grade})', fontweight='bold')

    for bar, score in zip(bars2, dim_scores):
        ax2.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2, f'{score:.1f}%', va='center', fontweight='bold', fontsize=10)

    plt.tight_layout()
    filename = f'reports/dq_scorecard_{title_suffix.lower().replace(" ", "_")}.png'
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'Chart disimpan: {filename}')


# ───────────────────────── 7. YDATA PROFILING REPORT ─────────────────────────
# Korelasi kategorik (phi_k/cramers) & interaksi numerik dimatikan karena kolom
# identitas (NIB/NPWP/NAMA/ALAMAT) berkardinalitas sangat tinggi (~hampir unik
# per baris) sehingga perhitungan contingency table-nya sangat lambat & tidak
# informatif untuk profiling ini.
YDATA_CORRELATIONS = {
    "auto": {"calculate": False},
    "pearson": {"calculate": True},
    "spearman": {"calculate": False},
    "kendall": {"calculate": False},
    "phi_k": {"calculate": False},
    "cramers": {"calculate": False},
}


def generate_ydata_report(df, name, output_path):
    print(f"\nMembuat ydata_profiling report untuk {name} -> {output_path} ...")
    profile = ProfileReport(
        df,
        title=f'Data Profiling Report — {name} (Before MDM)',
        explorative=True,
        correlations=YDATA_CORRELATIONS,
        interactions={"continuous": False},
    )
    profile.to_file(output_path)
    print(f"Report disimpan: {output_path}")


def build_profiling_index(summary, output_path='reports/profiling_before.html'):
    """Halaman index ringkas yang menggabungkan hasil profiling OSS & CEISA
    (overview, missing value, duplikat, format validation, baseline DQ score)
    serta link ke laporan ydata_profiling lengkap masing-masing dataset."""

    def fmt_checks(checks):
        rows = ''.join(
            f"<tr><td>{label}</td><td>{valid:,}</td><td>{total:,}</td><td>{valid / total * 100 if total else 0:.2f}%</td></tr>"
            for label, (valid, total) in checks.items()
        )
        return f"<table><tr><th>Check</th><th>Valid</th><th>Total</th><th>%</th></tr>{rows}</table>"

    def fmt_missing(table):
        if table.empty:
            return "<p>Tidak ada missing value.</p>"
        rows = ''.join(
            f"<tr><td>{idx}</td><td>{row.n_missing:,}</td><td>{row.pct_missing:.2f}%</td><td>{row.severity}</td></tr>"
            for idx, row in table.iterrows()
        )
        return f"<table><tr><th>Kolom</th><th>Jumlah Missing</th><th>% Missing</th><th>Severity</th></tr>{rows}</table>"

    def fmt_dq(metrics):
        rows = ''.join(f"<tr><td>{k}</td><td>{v:.2f}%</td></tr>" for k, v in metrics.items())
        avg = np.mean(list(metrics.values()))
        return f"<table><tr><th>Dimensi DMBOK</th><th>Score</th></tr>{rows}<tr><th>Overall</th><th>{avg:.2f}%</th></tr></table>"

    html = f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<title>Data Profiling Report - Before MDM (Tahap 1)</title>
<style>
  body {{ font-family: Arial, Helvetica, sans-serif; margin: 40px; color: #222; }}
  h1 {{ color: #1565C0; }}
  h2 {{ border-bottom: 2px solid #1565C0; padding-bottom: 4px; margin-top: 40px; }}
  table {{ border-collapse: collapse; margin: 10px 0 20px 0; width: 100%; max-width: 800px; }}
  th, td {{ border: 1px solid #ccc; padding: 6px 10px; text-align: left; font-size: 14px; }}
  th {{ background: #1565C0; color: white; }}
  tr:nth-child(even) {{ background: #f5f5f5; }}
  .summary {{ background: #E3F2FD; padding: 12px 16px; border-radius: 6px; }}
  a.btn {{ display: inline-block; margin: 8px 12px 8px 0; padding: 8px 16px; background: #1565C0;
           color: white; text-decoration: none; border-radius: 4px; }}
</style>
</head>
<body>
<h1>Data Profiling Report — Before MDM (Tahap 1)</h1>
<p class="summary">
  Mini Project Kelompok 5 (DJBC) — Master Data Importir &amp; Eksportir Nasional.<br>
  Profiling dilakukan terhadap data <b>OSS</b> ({summary['n_oss']:,} baris) dan
  <b>CEISA</b> ({summary['n_ceisa']:,} baris) sebelum proses cleansing &amp; Golden Record.
</p>

<h2>Laporan ydata_profiling Lengkap</h2>
<a class="btn" href="profiling_before_oss.html">OSS — Full Profiling Report</a>
<a class="btn" href="profiling_before_ceisa.html">CEISA — Full Profiling Report</a>

<h2>1. Dataset Overview</h2>
<table>
<tr><th>Dataset</th><th>Jumlah Baris</th><th>Jumlah Kolom</th></tr>
<tr><td>OSS</td><td>{summary['n_oss']:,}</td><td>{summary['n_cols_oss']}</td></tr>
<tr><td>CEISA</td><td>{summary['n_ceisa']:,}</td><td>{summary['n_cols_ceisa']}</td></tr>
</table>

<h2>2. Missing Value Analysis</h2>
<h3>OSS</h3>
{fmt_missing(summary['missing_oss'])}
<h3>CEISA</h3>
{fmt_missing(summary['missing_ceisa'])}

<h2>3. Duplicate Analysis</h2>
<table>
<tr><th>Metrik</th><th>OSS</th><th>CEISA</th></tr>
<tr><td>Full duplicate (baris identik)</td><td>{summary['dup_oss']['full_duplicate']:,}</td><td>{summary['dup_ceisa']['full_duplicate']:,}</td></tr>
<tr><td>Duplicate by NIB</td><td>{summary['dup_oss']['duplicate_by_nib']:,}</td><td>{summary['dup_ceisa']['duplicate_by_nib']:,}</td></tr>
</table>
<p><i>Catatan: Duplicate by NIB di OSS adalah anomali (NIB harus unik), sedangkan di CEISA sebagian besar
adalah Data Mart Snapshot Duplicate (expected) — lihat <code>docs/02_business_rules.md</code> Section 5.</i></p>

<h2>4. Format Validation</h2>
<h3>OSS</h3>
{fmt_checks(summary['fmt_oss'])}
<h3>CEISA</h3>
{fmt_checks(summary['fmt_ceisa'])}

<h2>5. Baseline Data Quality Score (4 Dimensi DMBOK)</h2>
<h3>OSS</h3>
{fmt_dq(summary['dq_oss'])}
<h3>CEISA</h3>
{fmt_dq(summary['dq_ceisa'])}

<p><i>Generated by Source/step05_profiling.py</i></p>
</body>
</html>
"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\nProfiling index disimpan: {output_path}")


if __name__ == "__main__":
    df_oss = pd.read_csv('data/raw/oss_nib_data.csv')
    df_ceisa = pd.read_csv('data/raw/ceisa_data.csv')

    # 1. Dataset overview
    dataset_overview(df_oss, 'OSS')
    dataset_overview(df_ceisa, 'CEISA')

    # 2. Statistik deskriptif
    descriptive_stats(df_oss, 'OSS')
    descriptive_stats(df_ceisa, 'CEISA')

    # 3. Missing value analysis
    missing_oss = missing_value_analysis(df_oss, 'OSS')
    missing_ceisa = missing_value_analysis(df_ceisa, 'CEISA')

    # 4. Duplicate analysis
    dup_oss = duplicate_analysis(df_oss, 'OSS', 'NAMA_PERSEROAN')
    dup_ceisa = duplicate_analysis(df_ceisa, 'CEISA', 'NAMA_PERUSAHAAN')

    # 5. Format validation
    fmt_oss = format_validation(df_oss, 'OSS')
    fmt_ceisa = format_validation(df_ceisa, 'CEISA')

    # 6. Baseline Data Quality Score
    print(f"\n{'='*65}\n 6. BASELINE DATA QUALITY SCORE (4 DIMENSI DMBOK)\n{'='*65}")
    oss_metrics = calculate_dq_metrics(df_oss, "OSS")
    ceisa_metrics = calculate_dq_metrics(df_ceisa, "CEISA")
    generate_professional_scorecard(oss_metrics, "OSS Master")
    generate_professional_scorecard(ceisa_metrics, "CEISA Operational")

    print("\n" + "=" * 45)
    print("   FINAL BASELINE DMBOK SUMMARY (4-DIM)")
    print("=" * 45)
    for dim in oss_metrics:
        print(f"  {dim:<18}: OSS {oss_metrics[dim]:6.2f}%  |  CEISA {ceisa_metrics[dim]:6.2f}%")
    print("-" * 45)
    print(f"  {'Overall':<18}: OSS {np.mean(list(oss_metrics.values())):6.2f}%  |  "
          f"CEISA {np.mean(list(ceisa_metrics.values())):6.2f}%")
    print("=" * 45)

    # 7. ydata_profiling reports
    print(f"\n{'='*65}\n 7. YDATA PROFILING REPORT\n{'='*65}")
    generate_ydata_report(df_oss, 'OSS', 'reports/profiling_before_oss.html')
    generate_ydata_report(df_ceisa, 'CEISA', 'reports/profiling_before_ceisa.html')

    summary = {
        'n_oss': len(df_oss), 'n_cols_oss': df_oss.shape[1],
        'n_ceisa': len(df_ceisa), 'n_cols_ceisa': df_ceisa.shape[1],
        'missing_oss': missing_oss, 'missing_ceisa': missing_ceisa,
        'dup_oss': dup_oss, 'dup_ceisa': dup_ceisa,
        'fmt_oss': fmt_oss, 'fmt_ceisa': fmt_ceisa,
        'dq_oss': oss_metrics, 'dq_ceisa': ceisa_metrics,
    }
    build_profiling_index(summary, 'reports/profiling_before.html')

    print("\n✅ Tahap 1 - Data Profiling selesai.")
