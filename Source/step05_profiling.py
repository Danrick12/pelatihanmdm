# [LAB 2] DATA PROFILING & DQ SCORECARD (TAHAP 1)
# Berdasarkan: docs/02_business_rules.md (DMBOK 4-Dimension)

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import re
from datetime import datetime

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
    v_nib = df['NIB'].astype(str).str.match(r'^\d{13}$').mean() * 100
    npwp_col = 'NPWP_PERSEROAN' if dataset_name == "OSS" else 'NPWP'
    v_npwp = df[npwp_col].astype(str).str.match(r'^\d{2}\.\d{3}\.\d{3}\.\d{1}-\d{3}\.\d{3}$').mean() * 100
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
    
    if total_dq_score >= TARGET_SCORE: grade, grade_color = 'A (Excellent)', '#4CAF50'
    elif total_dq_score >= WARNING_SCORE: grade, grade_color = 'B (Good)', '#8BC34A'
    elif total_dq_score >= 60: grade, grade_color = 'C (Fair)', '#FF9800'
    else: grade, grade_color = 'D (Poor)', '#F44336'

    fig = plt.figure(figsize=(16, 8))
    fig.suptitle(f'Data Quality Scorecard \u2014 {title_suffix} (Before MDM)', fontsize=16, fontweight='bold', y=1.05)

    # ── Chart 1: Radar Chart (Hexagon) ──
    angles = np.linspace(0, 2*np.pi, len(dim_names), endpoint=False).tolist()
    dim_scores_polar = dim_scores + [dim_scores[0]]
    angles += [angles[0]]

    ax1 = plt.subplot(121, polar=True)
    ax1.set_theta_offset(np.pi / 2)
    ax1.set_theta_direction(-1)

    ax1.plot(angles, dim_scores_polar, 'o-', linewidth=3, color='#2196F3', markersize=8)
    ax1.fill(angles, dim_scores_polar, alpha=0.3, color='#2196F3')
    ax1.plot(angles, [TARGET_SCORE]*len(angles), '--', color='red', alpha=0.6, label=f'Target {TARGET_SCORE}%')
    
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
        ax2.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2, f'{score:.1f}%', va='center', fontweight='bold', fontsize=10)

    plt.tight_layout()
    filename = f'reports/dq_scorecard_{title_suffix.lower().replace(" ", "_")}.png'
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f'💾 Chart disimpan: {filename}')
    plt.show()

if __name__ == "__main__":
    try:
        df_oss = pd.read_csv('data/raw/oss_nib_data.csv')
        df_ceisa = pd.read_csv('data/raw/ceisa_data.csv')

        print("\n📊 Generating 4-Dimension Scorecard for OSS Master...")
        oss_metrics = calculate_dq_metrics(df_oss, "OSS")
        generate_professional_scorecard(oss_metrics, "OSS Master")

        print("\n📊 Generating 4-Dimension Scorecard for CEISA Operational...")
        ceisa_metrics = calculate_dq_metrics(df_ceisa, "CEISA")
        generate_professional_scorecard(ceisa_metrics, "CEISA Operational")

        print("\n" + "="*45)
        print("   FINAL BASELINE DMBOK SUMMARY (4-DIM)")
        print("="*45)
        print(f"OSS Master Overall Score      : {np.mean(list(oss_metrics.values())):.1f}/100")
        print(f"CEISA Operational Overall Score: {np.mean(list(ceisa_metrics.values())):.1f}/100")
        print("="*45)

    except Exception as e:
        print(f"❌ Error: {e}")
