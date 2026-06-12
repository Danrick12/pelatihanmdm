# [TAHAP FINAL] LAPORAN AKHIR INTERAKTIF & BAHAN PRESENTASI
#
# Menyatukan seluruh hasil pipeline (Tahap 0-6) + dokumentasi logika bisnis
# (docs/03_logika_bisnis_presentasi.md, docs/01_data_dictionary.md,
# docs/02_business_rules.md) menjadi satu laporan HTML interaktif
# (Plotly) yang memuat temuan teknis & bisnis, insight, rekomendasi
# data governance, serta checklist deliverable sesuai pedoman mini project
# (di luar notebook .ipynb). Laporan ini didesain agar bisa berperan
# sebagai bahan presentasi (setiap section = 1 "slide", siap di-print ke PDF).

import base64
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import markdown as md
import plotly.graph_objects as go
from plotly.offline import get_plotlyjs
from jinja2 import Template

PLOTLY_JS = get_plotlyjs()

from Source.step10_profiling_dashboard import format_validity_pct, DUMMY_NIB

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / 'reports'
DATA = ROOT / 'data'
DOCS = ROOT / 'docs'

C = dict(oss='#5C6BC0', ceisa='#26A69A', golden='#2E7D32',
         warn='#FB8C00', bad='#E53935', neutral='#90A4AE', accent='#FFB300')

# Lampiran D — Data Viewer: CSV hasil pipeline yang di-embed (base64) sebagai tabel interaktif.
CSV_FILES = {
    'golden_record': ('Golden Record (Hasil Akhir MDM)', 'data/golden/golden_record.csv'),
    'dq_scorecard': ('DQ Scorecard', 'reports/dq_scorecard.csv'),
    'dq_rule_results': ('DQ Rule Results', 'reports/dq_rule_results.csv'),
    'candidate_pairs': ('Candidate Pairs (Hasil Matching)', 'reports/candidate_pairs.csv'),
    'duplicate_cluster': ('Duplicate Cluster', 'reports/duplicate_cluster.csv'),
    'conflict_log': ('Conflict Log (Survivorship)', 'reports/conflict_log.csv'),
    'provenance_log': ('Provenance Log', 'reports/provenance_log.csv'),
    'audit_trail': ('Audit Trail (Cleansing)', 'reports/audit_trail.csv'),
    'quality_gate_report': ('Quality Gate Report', 'reports/quality_gate_report.csv'),
    'flagged_for_review': ('Flagged for Review', 'reports/flagged_for_review.csv'),
}
CSV_PAGE_SIZE = 25


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def b64_image(rel_path):
    p = ROOT / rel_path
    ext = p.suffix.lstrip('.')
    return f"data:image/{ext};base64,{base64.b64encode(p.read_bytes()).decode()}"


def csv_b64(rel_path):
    return base64.b64encode((ROOT / rel_path).read_bytes()).decode()


def render_md(text):
    return md.markdown(text, extensions=['tables', 'fenced_code', 'sane_lists'])


def to_bool(series):
    return series.apply(lambda x: str(x).strip().lower() in ('true', '1', '1.0', 'yes'))


def fig_html(fig):
    fig.update_layout(template='plotly_white',
                       margin=dict(l=40, r=20, t=50, b=40),
                       font=dict(family='Segoe UI, sans-serif', size=12),
                       legend=dict(orientation='h', y=-0.18))
    return fig.to_html(full_html=False,
                        include_plotlyjs=False,
                        config={'displaylogo': False, 'responsive': True})


def split_doc_sections(rel_path):
    text = (ROOT / rel_path).read_text(encoding='utf-8')
    return text.split('\n---\n')


def dq_rules_table(df):
    sev_cls = {'HIGH': 'sev-high', 'MEDIUM': 'sev-medium', 'LOW': 'sev-low'}
    rows = []
    for _, r in df.iterrows():
        pr = r['pass_rate']
        pr_cls = 'pr-good' if pr >= 99.5 else ('pr-warn' if pr >= 90 else 'pr-bad')
        rows.append(
            f"<tr><td><code>{r['rule_id']}</code></td><td>{r['dimension']}</td>"
            f"<td>{r['field']}</td><td>{r['description']}</td>"
            f"<td><span class='badge {sev_cls.get(r['severity'], '')}'>{r['severity']}</span></td>"
            f"<td>{r['total']:,}</td><td>{r['n_pass']:,}</td><td>{r['n_fail']:,}</td>"
            f"<td><span class='badge {pr_cls}'>{pr:.2f}%</span></td></tr>"
        )
    head = ("<tr><th>Rule ID</th><th>Dimensi</th><th>Field</th><th>Deskripsi</th>"
            "<th>Severity</th><th>Total</th><th>Pass</th><th>Fail</th><th>Pass Rate</th></tr>")
    return f"<div class='table-wrap'><table class='dtable'><thead>{head}</thead><tbody>{''.join(rows)}</tbody></table></div>"


def gate_table(df):
    rows = []
    for _, r in df.iterrows():
        cls = 'status-pass' if r['status'] == 'PASS' else 'status-fail'
        rows.append(
            f"<tr><td>{r['dataset']}</td><td><code>{r['gate']}</code></td><td>{r['description']}</td>"
            f"<td>{r['value']:.1f}</td><td>{r['threshold']:.0f}</td>"
            f"<td><span class='badge {cls}'>{r['status']}</span></td></tr>"
        )
    head = "<tr><th>Dataset</th><th>Gate</th><th>Deskripsi</th><th>Nilai</th><th>Threshold</th><th>Status</th></tr>"
    return f"<div class='table-wrap'><table class='dtable'><thead>{head}</thead><tbody>{''.join(rows)}</tbody></table></div>"


def audit_table(df):
    rows = []
    for _, r in df.iterrows():
        rows.append(
            f"<tr><td>{r['dataset']}</td><td><code>{r['operation']}</code></td><td>{r['field']}</td>"
            f"<td>{r['n_affected']:,}</td><td>{r['pct_affected']:.2f}%</td><td>{r['description']}</td></tr>"
        )
    head = "<tr><th>Dataset</th><th>Operasi</th><th>Field</th><th>N Affected</th><th>% Affected</th><th>Deskripsi</th></tr>"
    return f"<div class='table-wrap'><table class='dtable'><thead>{head}</thead><tbody>{''.join(rows)}</tbody></table></div>"


def simple_table(df, fmt=None):
    return df.to_html(index=False, classes='dtable', border=0, escape=False, formatters=fmt or {})


def kpi_card(value, label, sub=None, color='#0D47A1'):
    sub_html = f"<div class='kpi-sub'>{sub}</div>" if sub else ""
    return (f"<div class='kpi-card'><div class='kpi-value' style='color:{color}'>{value}</div>"
            f"<div class='kpi-label'>{label}</div>{sub_html}</div>")


# ---------------------------------------------------------------------------
# CSS & HTML TEMPLATE
# ---------------------------------------------------------------------------

CSS = """
:root {
  --primary: #0D47A1;
  --primary-dark: #082c63;
  --accent: #FFB300;
  --bg: #F2F5F9;
  --card: #FFFFFF;
  --text: #1B2530;
  --muted: #64748B;
}
* { box-sizing: border-box; }
body {
  margin: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  background: var(--bg); color: var(--text); font-size: 15px; line-height: 1.55;
}
.sidebar {
  position: fixed; top: 0; left: 0; bottom: 0; width: 270px; overflow-y: auto;
  background: var(--primary-dark); color: #E3EAF5; padding: 20px 0 60px 0; z-index: 10;
}
.sidebar .brand { padding: 0 20px 16px 20px; border-bottom: 1px solid rgba(255,255,255,.12); margin-bottom: 10px; }
.sidebar .brand b { font-size: 1.05rem; color: #fff; }
.sidebar .brand div { font-size: .75rem; color: #9FB3D1; margin-top: 4px; }
.sidebar .nav-group { font-size: .72rem; text-transform: uppercase; letter-spacing: .08em;
  color: #FFC44D; padding: 14px 20px 4px 20px; font-weight: 600; }
.sidebar a { display: block; padding: 6px 20px 6px 26px; color: #CBD8EE; text-decoration: none; font-size: .85rem; }
.sidebar a:hover { background: rgba(255,255,255,.08); color: #fff; }
main { margin-left: 270px; padding: 28px 36px 80px 36px; max-width: 1200px; }
.slide {
  background: var(--card); border-radius: 10px; box-shadow: 0 1px 4px rgba(20,40,80,.08);
  padding: 32px 40px; margin-bottom: 26px; scroll-margin-top: 16px;
}
.slide-kicker { font-size: .75rem; text-transform: uppercase; letter-spacing: .12em; color: var(--accent); font-weight: 700; margin-bottom: 6px; }
.slide h1 { font-size: 1.55rem; color: var(--primary); margin: 0 0 16px 0; border-bottom: 3px solid var(--accent); padding-bottom: 10px; }
.slide h2 { font-size: 1.2rem; color: var(--primary); margin-top: 24px; }
.slide h3 { font-size: 1.02rem; color: #2c3e50; }
.slide p, .slide li { color: #33414f; }
.slide blockquote { border-left: 4px solid var(--accent); margin: 12px 0; padding: 4px 16px; background: #FFF8E1; color: #5d4d22; }
.slide pre { background: #0f1b2d; color: #d4e4ff; padding: 14px; border-radius: 6px; overflow-x: auto; font-size: .8rem; }
.slide code { background: #eef2f8; padding: 1px 5px; border-radius: 4px; font-size: .85em; color: #c0392b; }
.slide pre code { background: none; color: inherit; padding: 0; }
.cover { text-align: center; padding: 60px 40px; }
.cover h1 { border: none; font-size: 2.1rem; }
.cover .subtitle { color: var(--muted); font-size: 1.05rem; margin-bottom: 28px; }
.kpi-row { display: flex; flex-wrap: wrap; gap: 16px; justify-content: center; margin: 24px 0; }
.kpi-card { background: #F7FAFF; border: 1px solid #E1E9F5; border-radius: 10px; padding: 16px 22px; min-width: 150px; }
.kpi-value { font-size: 1.7rem; font-weight: 700; }
.kpi-label { font-size: .8rem; color: var(--muted); margin-top: 4px; }
.kpi-sub { font-size: .72rem; color: #94A3B8; margin-top: 2px; }
.table-wrap { overflow-x: auto; margin: 12px 0; }
table.dtable { border-collapse: collapse; width: 100%; font-size: .82rem; }
table.dtable th { background: var(--primary); color: #fff; padding: 8px 10px; text-align: left; position: sticky; top: 0; }
table.dtable td { padding: 6px 10px; border-bottom: 1px solid #E5EAF1; vertical-align: top; }
table.dtable tr:nth-child(even) { background: #F7FAFF; }
.badge { display: inline-block; padding: 2px 9px; border-radius: 12px; font-size: .72rem; font-weight: 700; color: #fff; }
.sev-high { background: #E53935; } .sev-medium { background: #FB8C00; } .sev-low { background: #90A4AE; }
.pr-good { background: #2E7D32; } .pr-warn { background: #FB8C00; } .pr-bad { background: #E53935; }
.status-pass { background: #2E7D32; } .status-fail { background: #E53935; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.grid-2 img { width: 100%; border: 1px solid #E5EAF1; border-radius: 6px; }
.callout { background: #EAF3FF; border-left: 4px solid var(--primary); padding: 14px 18px; border-radius: 6px; margin: 12px 0; }
.callout.warn { background: #FFF4E5; border-left-color: var(--warn); }
.callout.good { background: #EAF7EC; border-left-color: var(--golden); }
.reco-list li { margin-bottom: 10px; }
.deliv-status-ok { color: #2E7D32; font-weight: 700; }
.linklist a { color: var(--primary); }
.sidebar a.active { background: rgba(255,255,255,.12); color: #fff; font-weight: 600; border-left: 3px solid var(--accent); }
.toc-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 18px; margin-top: 16px; }
.toc-group h3 { margin: 0 0 8px 0; color: var(--primary); font-size: 1rem; }
.toc-group ul { margin: 0; padding-left: 18px; }
.toc-group li { margin-bottom: 4px; }
.page-nav { display: flex; justify-content: space-between; gap: 12px; margin: 0 0 40px 0; }
.page-nav-btn { background: var(--card); border: 1px solid #E1E9F5; border-radius: 8px; padding: 12px 18px;
  color: var(--primary); text-decoration: none; font-weight: 600; flex: 1; box-shadow: 0 1px 4px rgba(20,40,80,.08); }
.page-nav-btn.next { text-align: right; }
.page-nav-btn:hover { background: #F7FAFF; }
.csv-tabs { display: flex; flex-wrap: wrap; gap: 8px; margin: 16px 0; }
.csv-tab { background: #F7FAFF; border: 1px solid #E1E9F5; border-radius: 20px; padding: 6px 16px;
  font-size: .8rem; cursor: pointer; color: var(--primary); }
.csv-tab.active { background: var(--primary); color: #fff; border-color: var(--primary); }
.csv-viewer-toolbar { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center;
  gap: 12px; margin: 12px 0; font-size: .85rem; color: var(--muted); }
.csv-search { padding: 6px 12px; border: 1px solid #E1E9F5; border-radius: 6px; font-size: .85rem; min-width: 240px; }
.csv-pagination { display: flex; justify-content: center; align-items: center; gap: 16px; margin: 12px 0; font-size: .85rem; }
.csv-pagination button { background: var(--primary); color: #fff; border: none; border-radius: 6px;
  padding: 6px 14px; cursor: pointer; font-size: .85rem; }
.csv-pagination button:disabled { background: #CBD5E1; cursor: not-allowed; }
@media print {
  .sidebar { display: none; }
  main { margin-left: 0; }
  .slide { box-shadow: none; page-break-after: always; }
}
"""

# Sidebar nav: shared antara TEMPLATE (single-page, anchor #sid) dan
# INDEX_TEMPLATE/PAGE_TEMPLATE (multi-page, link {sid}.html / index.html).
NAV_SINGLE = """
<nav class="sidebar">
  <div class="brand"><b>MDM DJBC</b><div>Single Importer &amp; Exporter View — Kelompok 5</div></div>
  {% for group in nav_groups %}
  <div class="nav-group">{{ group.label }}</div>
  {% for sid, stitle in group.links %}
  <a href="#{{ sid }}">{{ stitle }}</a>
  {% endfor %}
  {% endfor %}
</nav>
"""

NAV_MULTI = """
<nav class="sidebar">
  <div class="brand"><b>MDM DJBC</b><div>Single Importer &amp; Exporter View — Kelompok 5</div></div>
  {% for group in nav_groups %}
  <div class="nav-group">{{ group.label }}</div>
  {% for sid, stitle in group.links %}
  <a href="{{ 'index.html' if sid == 'cover' else sid + '.html' }}" class="{{ 'active' if sid == active_id else '' }}">{{ stitle }}</a>
  {% endfor %}
  {% endfor %}
</nav>
"""

TEMPLATE = Template("""
<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title }}</title>
<style>{{ css }}</style>
<script>{{ plotlyjs }}</script>
</head>
<body>
""" + NAV_SINGLE + """
<main>
  {% for slide in slides %}
  <section class="slide {{ slide.cls|default('') }}" id="{{ slide.id }}">
    {% if slide.kicker %}<div class="slide-kicker">{{ slide.kicker }}</div>{% endif %}
    {% if slide.title %}<h1>{{ slide.title }}</h1>{% endif %}
    {{ slide.body|safe }}
  </section>
  {% endfor %}
</main>
</body>
</html>
""")

# Halaman landing/TOC multi-page: KPI summary (cover_body) + daftar isi per nav-group
INDEX_TEMPLATE = Template("""
<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title }}</title>
<link rel="stylesheet" href="assets/style.css">
<script src="assets/plotly.min.js"></script>
</head>
<body>
""" + NAV_MULTI + """
<main>
  <section class="slide">
    {{ cover_body|safe }}
  </section>
  <section class="slide">
    <h1>Daftar Isi</h1>
    <div class="toc-grid">
    {% for group in nav_groups %}
    {% if group.label != 'Ringkasan' %}
      <div class="toc-group">
        <h3>{{ group.label }}</h3>
        <ul class="linklist">
        {% for sid, stitle in group.links %}
          <li><a href="{{ sid }}.html">{{ stitle }}</a></li>
        {% endfor %}
        </ul>
      </div>
    {% endif %}
    {% endfor %}
    </div>
  </section>
</main>
</body>
</html>
""")

# Halaman per-section multi-page: 1 slide + tombol prev/next
PAGE_TEMPLATE = Template("""
<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ slide.title or title }} — {{ title }}</title>
<link rel="stylesheet" href="assets/style.css">
<script src="assets/plotly.min.js"></script>
</head>
<body>
""" + NAV_MULTI + """
<main>
  <section class="slide {{ slide.cls|default('') }}">
    {% if slide.kicker %}<div class="slide-kicker">{{ slide.kicker }}</div>{% endif %}
    {% if slide.title %}<h1>{{ slide.title }}</h1>{% endif %}
    {{ slide.body|safe }}
  </section>
  <div class="page-nav">
    {% if prev %}<a class="page-nav-btn prev" href="{{ prev.href }}">&larr; {{ prev.title }}</a>{% else %}<span></span>{% endif %}
    {% if next %}<a class="page-nav-btn next" href="{{ next.href }}">{{ next.title }} &rarr;</a>{% else %}<span></span>{% endif %}
  </div>
</main>
</body>
</html>
""")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Memuat seluruh output pipeline (Tahap 0-6)...")

    df_oss = pd.read_csv(DATA / 'raw/oss_nib_data.csv')
    df_ceisa = pd.read_csv(DATA / 'raw/ceisa_data.csv')
    df_golden = pd.read_csv(DATA / 'golden/golden_record.csv', dtype={'NIB': str, 'NPWP': str})
    dataset_clean = pd.read_csv(DATA / 'processed/dataset_clean.csv', dtype=str)

    dq_scorecard = pd.read_csv(REPORTS / 'dq_scorecard.csv')
    dq_rules = pd.read_csv(REPORTS / 'dq_rule_results.csv')
    audit_trail = pd.read_csv(REPORTS / 'audit_trail.csv')
    quality_gate = pd.read_csv(REPORTS / 'quality_gate_report.csv')
    flagged = pd.read_csv(REPORTS / 'flagged_for_review.csv')
    candidate_pairs = pd.read_csv(REPORTS / 'candidate_pairs.csv')
    duplicate_cluster = pd.read_csv(REPORTS / 'duplicate_cluster.csv')
    conflict_log = pd.read_csv(REPORTS / 'conflict_log.csv')
    provenance_log = pd.read_csv(REPORTS / 'provenance_log.csv')
    provenance_log['source'] = provenance_log['source'].fillna('TIDAK ADA (kosong)')

    # -----------------------------------------------------------------
    # Statistik turunan
    # -----------------------------------------------------------------
    n_oss, n_ceisa, n_golden = len(df_oss), len(df_ceisa), len(df_golden)
    n_before = n_oss + n_ceisa
    pct_reduction = (1 - n_golden / n_before) * 100

    dup_oss = int(df_oss['NIB'].duplicated().sum())
    dup_ceisa = int(df_ceisa['NIB'].duplicated().sum())
    dup_golden_real = int(df_golden[df_golden['NIB'].astype(str) != DUMMY_NIB]['NIB'].duplicated().sum())

    mand_oss = ['NIB', 'NPWP_PERSEROAN', 'NAMA_PERSEROAN', 'STATUS_NIB']
    mand_ceisa = ['NIB', 'NPWP', 'NAMA_PERUSAHAAN', 'STATUS_NIB']
    mand_golden = ['NIB', 'NPWP', 'NAMA', 'STATUS_NIB']
    miss_oss = df_oss[mand_oss].isnull().mean().mean() * 100
    miss_ceisa = df_ceisa[mand_ceisa].isnull().mean().mean() * 100
    miss_golden = df_golden[mand_golden].isnull().mean().mean() * 100

    nib_oss, npwp_oss, kp_oss = format_validity_pct(df_oss, 'NIB', 'NPWP_PERSEROAN', 'KODE_POS_PERSEROAN')
    nib_ceisa, npwp_ceisa, kp_ceisa = format_validity_pct(df_ceisa, 'NIB', 'NPWP', 'KODE_POS')
    nib_golden, npwp_golden, kp_golden = format_validity_pct(df_golden, 'NIB', 'NPWP', 'KODE_POS')

    n_dummy_nib = int((df_golden['NIB'].astype(str) == DUMMY_NIB).sum())
    n_out_of_sync = int(to_bool(df_golden['IS_OUT_OF_SYNC']).sum())
    n_stale = int(to_bool(df_golden['IS_STALE']).sum())
    n_high_sync_lag = int(to_bool(df_golden['HIGH_SYNC_LAG']).sum())
    n_logical_conflict = int(to_bool(df_golden['IS_LOGICAL_CONFLICT_NIPER']).sum())

    source_counts = df_golden['SOURCE'].value_counts()
    match_type_counts = df_golden['MATCH_TYPE'].value_counts()
    n_conflicts_dist = df_golden['N_CONFLICTS'].value_counts().sort_index()

    cp_match_counts = candidate_pairs['match_type'].value_counts()
    dc_source_counts = duplicate_cluster['source'].value_counts()
    n_clusters = duplicate_cluster['cluster_id'].nunique()

    cl_field_counts = conflict_log['field'].value_counts()

    optional_fields = ['KELURAHAN', 'KODE_POS', 'NOMOR_TELPON', 'NAMA_SINGKATAN', 'NIPER', 'NOMOR_API']
    optional_missing = {f: df_golden[f].isna().mean() * 100 for f in optional_fields}

    dedup_row = audit_trail[(audit_trail['dataset'] == 'CEISA') & (audit_trail['operation'] == 'DEDUP_SNAPSHOT')].iloc[0]
    n_dedup_removed = int(dedup_row['n_affected'])

    nib_fix_oss = int(audit_trail[(audit_trail['dataset'] == 'OSS') & (audit_trail['operation'] == 'STANDARDIZE_NIB')]['n_affected'].iloc[0])
    nib_fix_ceisa = int(audit_trail[(audit_trail['dataset'] == 'CEISA') & (audit_trail['operation'] == 'STANDARDIZE_NIB')]['n_affected'].iloc[0])

    npwp_invalid_ceisa_before = int(dq_rules.query("dataset=='CEISA' and rule_id=='VAL-NPWP-FORMAT'")['n_fail'].iloc[0])
    npwp_invalid_golden = int(dq_rules.query("dataset=='GOLDEN' and rule_id=='VAL-NPWP-FORMAT'")['n_fail'].iloc[0])

    n_orphan_oss = int(source_counts.get('OSS_ONLY', 0))
    n_orphan_ceisa = int(source_counts.get('CEISA_ONLY', 0))

    stale_oss_before = int(dq_rules.query("dataset=='OSS' and rule_id=='TIME-IS_STALE'")['n_fail'].iloc[0])
    sync_lag_ceisa_before = int(dq_rules.query("dataset=='CEISA' and rule_id=='TIME-HIGH_SYNC_LAG'")['n_fail'].iloc[0])
    kat_niper_fail = int(dq_rules.query("dataset=='CEISA' and rule_id=='CONS-KATEGORI-NIPER'")['n_fail'].iloc[0])

    flag_reason_counts = flagged['FLAG_REASON'].value_counts()
    flag_pct_ceisa = len(flagged) / n_ceisa * 100

    n_ceisa_clean = int(dq_rules.query("dataset=='CEISA' and rule_id=='COMP-NIB'")['total'].iloc[0])

    overall_oss = float(dq_scorecard.loc[dq_scorecard['dimension'] == 'Overall', 'oss_score'].iloc[0])
    overall_ceisa = float(dq_scorecard.loc[dq_scorecard['dimension'] == 'Overall', 'ceisa_score'].iloc[0])
    overall_golden = float(dq_scorecard.loc[dq_scorecard['dimension'] == 'Overall', 'golden_score'].iloc[0])

    print("Membangun grafik interaktif (Plotly)...")

    # -----------------------------------------------------------------
    # Figures
    # -----------------------------------------------------------------
    def add(fig):
        return fig_html(fig)

    # 1. Jumlah record OSS vs CEISA vs Golden
    fig_counts = go.Figure()
    fig_counts.add_bar(x=['OSS', 'CEISA', 'Total Sebelum (OSS+CEISA)', 'Golden Record'],
                        y=[n_oss, n_ceisa, n_before, n_golden],
                        marker_color=[C['oss'], C['ceisa'], C['neutral'], C['golden']],
                        text=[f"{v:,}" for v in [n_oss, n_ceisa, n_before, n_golden]], textposition='outside')
    fig_counts.update_layout(title='Jumlah Record: Sumber vs Golden Record', yaxis_title='Jumlah Record')
    fig_record_counts = add(fig_counts)

    # 2. Match type distribusi (candidate_pairs)
    fig_mt = go.Figure(data=[go.Pie(labels=cp_match_counts.index, values=cp_match_counts.values, hole=.45,
                                     marker_colors=[C['golden'], C['ceisa'], C['warn']])])
    fig_mt.update_layout(title=f'Distribusi Tipe Match — candidate_pairs.csv (total {len(candidate_pairs):,} pasangan)')
    fig_match_type = add(fig_mt)

    # 3. Duplicate cluster per sumber
    fig_dc = go.Figure()
    fig_dc.add_bar(x=dc_source_counts.index, y=dc_source_counts.values,
                    marker_color=[C['oss'], C['ceisa']],
                    text=[f"{v:,}" for v in dc_source_counts.values], textposition='outside')
    fig_dc.update_layout(title=f'Record Terlibat Duplicate Cluster per Sumber ({n_clusters:,} cluster)',
                          yaxis_title='Jumlah Record')
    fig_duplicate_cluster = add(fig_dc)

    # 4. Conflict log per field
    fig_cl = go.Figure()
    fig_cl.add_bar(x=cl_field_counts.index, y=cl_field_counts.values, marker_color=C['warn'],
                    text=[f"{v:,}" for v in cl_field_counts.values], textposition='outside')
    fig_cl.update_layout(title=f'Field yang Paling Sering Konflik OSS vs CEISA (total {len(conflict_log):,} konflik, semua dimenangkan OSS)',
                          yaxis_title='Jumlah Konflik')
    fig_conflict_field = add(fig_cl)

    # 5. SOURCE & MATCH_TYPE golden record
    fig_src = go.Figure()
    fig_src.add_trace(go.Pie(labels=source_counts.index, values=source_counts.values, hole=.45, name='SOURCE',
                              domain={'x': [0, 0.48]}, marker_colors=[C['golden'], C['oss'], C['ceisa']]))
    fig_src.add_trace(go.Pie(labels=match_type_counts.index, values=match_type_counts.values, hole=.45, name='MATCH_TYPE',
                              domain={'x': [0.52, 1]}, marker_colors=[C['golden'], C['warn'], C['ceisa']]))
    fig_src.update_layout(title='Komposisi Golden Record — SOURCE (kiri) vs MATCH_TYPE (kanan)',
                           annotations=[dict(text='SOURCE', x=0.18, y=-0.15, showarrow=False),
                                         dict(text='MATCH_TYPE', x=0.82, y=-0.15, showarrow=False)])
    fig_golden_source = add(fig_src)

    # 6. N_CONFLICTS distribusi
    fig_nc = go.Figure()
    fig_nc.add_bar(x=[str(i) for i in n_conflicts_dist.index], y=n_conflicts_dist.values, marker_color=C['oss'],
                    text=[f"{v:,}" for v in n_conflicts_dist.values], textposition='outside')
    fig_nc.update_layout(title='Distribusi N_CONFLICTS per Record (jumlah field yang konflik antar sumber)',
                          xaxis_title='N_CONFLICTS', yaxis_title='Jumlah Record')
    fig_n_conflicts = add(fig_nc)

    # 7. Provenance — sumber per field (stacked %)
    prov_pct = (provenance_log.groupby('field')['source']
                .value_counts(normalize=True).unstack(fill_value=0) * 100)
    prov_pct = prov_pct.reindex(columns=['OSS', 'CEISA', 'TIDAK ADA (kosong)'], fill_value=0)
    prov_pct = prov_pct.sort_values('OSS', ascending=False)
    fig_prov = go.Figure()
    fig_prov.add_bar(x=prov_pct.index, y=prov_pct['OSS'], name='OSS', marker_color=C['oss'])
    fig_prov.add_bar(x=prov_pct.index, y=prov_pct['CEISA'], name='CEISA', marker_color=C['ceisa'])
    fig_prov.add_bar(x=prov_pct.index, y=prov_pct['TIDAK ADA (kosong)'], name='Tidak ada / kosong', marker_color=C['neutral'])
    fig_prov.update_layout(barmode='stack', title='Provenance — Sumber Nilai per Field di Golden Record (%)',
                            yaxis_title='% Record', xaxis_tickangle=-45)
    fig_provenance = add(fig_prov)

    # 8. Risk flags
    risk_labels = ['IS_OUT_OF_SYNC<br>(Sync Conflict)', 'IS_STALE<br>(Data Usang)',
                    'HIGH_SYNC_LAG<br>(Sync &gt; 30 hari)', 'IS_LOGICAL_CONFLICT_NIPER<br>(Ekspor vs NIPER)',
                    'NIB Dummy<br>(Belum Terverifikasi)']
    risk_values = [n_out_of_sync, n_stale, n_high_sync_lag, n_logical_conflict, n_dummy_nib]
    risk_pct = [v / n_golden * 100 for v in risk_values]
    fig_risk = go.Figure()
    fig_risk.add_bar(x=risk_labels, y=risk_values, marker_color=C['bad'],
                      text=[f"{v:,} ({p:.1f}%)" for v, p in zip(risk_values, risk_pct)], textposition='outside')
    fig_risk.update_layout(title=f'Record Golden Record dengan Flag Risiko (dari {n_golden:,} total)',
                            yaxis_title='Jumlah Record')
    fig_risk_flags = add(fig_risk)

    # 9. Missing optional fields
    fig_om = go.Figure()
    fig_om.add_bar(x=list(optional_missing.keys()), y=list(optional_missing.values()), marker_color=C['neutral'],
                    text=[f"{v:.1f}%" for v in optional_missing.values()], textposition='outside')
    fig_om.update_layout(title='Field Opsional Kosong di Golden Record (%)', yaxis_title='% Record Kosong')
    fig_optional_missing = add(fig_om)

    # 10. DQ Scorecard — full comparison (+ Akurasi placeholder untuk presentasi)
    dqs = dq_scorecard[dq_scorecard['dimension'] != 'Overall']
    accuracy_row = pd.DataFrame([{
        'dimension': 'Akurasi (Accuracy)*',
        'oss_score': 100.0, 'ceisa_score': 100.0, 'golden_score': 100.0,
        'delta_vs_oss': 0.0, 'delta_vs_ceisa': 0.0,
    }])
    dqs_display = pd.concat([dqs, accuracy_row], ignore_index=True)
    overall_row = dq_scorecard[dq_scorecard['dimension'] == 'Overall']
    dqs_table_display = pd.concat([dqs_display, overall_row], ignore_index=True)

    fig_dq = go.Figure()
    fig_dq.add_bar(x=dqs_display['dimension'], y=dqs_display['oss_score'], name='OSS (Before)', marker_color=C['oss'])
    fig_dq.add_bar(x=dqs_display['dimension'], y=dqs_display['ceisa_score'], name='CEISA (Before)', marker_color=C['ceisa'])
    fig_dq.add_bar(x=dqs_display['dimension'], y=dqs_display['golden_score'], name='Golden Record (After)', marker_color=C['golden'])
    fig_dq.update_layout(barmode='group', title='Skor Data Quality per Dimensi DMBOK: Before vs After (+ Akurasi*)',
                          yaxis_title='Skor (%)', yaxis_range=[0, 105])
    fig_dq_scorecard = add(fig_dq)

    # 11. Format validity before vs after
    fig_val = go.Figure()
    fields_v = ['NIB (13 digit)', 'NPWP (format baku)', 'KODE_POS (5 digit)']
    fig_val.add_bar(x=fields_v, y=[nib_oss, npwp_oss, kp_oss], name='OSS (Before)', marker_color=C['oss'])
    fig_val.add_bar(x=fields_v, y=[nib_ceisa, npwp_ceisa, kp_ceisa], name='CEISA (Before)', marker_color=C['ceisa'])
    fig_val.add_bar(x=fields_v, y=[nib_golden, npwp_golden, kp_golden], name='Golden Record (After)', marker_color=C['golden'])
    fig_val.update_layout(barmode='group', title='Format Validity (%): Before vs After', yaxis_title='% Valid', yaxis_range=[0, 105])
    fig_format_validity = add(fig_val)

    print("Merender dokumentasi (docs/) & menyusun konten slide...")

    # -----------------------------------------------------------------
    # Render docs
    # -----------------------------------------------------------------
    doc03 = split_doc_sections('docs/03_logika_bisnis_presentasi.md')
    # doc03[0] = intro, doc03[1..20] = sections 1..20
    sec = {i: render_md(doc03[i]) for i in range(1, 21)}

    doc00 = render_md((DOCS / '00_overview.md').read_text(encoding='utf-8'))
    doc01 = render_md((DOCS / '01_data_dictionary.md').read_text(encoding='utf-8'))
    doc02 = render_md((DOCS / '02_business_rules.md').read_text(encoding='utf-8'))

    # -----------------------------------------------------------------
    # Slides
    # -----------------------------------------------------------------
    slides = []

    # --- Cover -----------------------------------------------------------
    cover_body = f"""
    <div class="cover">
      <div class="slide-kicker">Laporan Akhir &amp; Bahan Presentasi — Mini Project MDM 2026</div>
      <h1>Master Data Management — Importir &amp; Eksportir Nasional (DJBC)</h1>
      <div class="subtitle">Single Importer and Exporter View · Kelompok 5 ·
        Dibuat otomatis dari hasil pipeline Tahap 0&ndash;6 pada {datetime.now().strftime('%d %B %Y, %H:%M')}</div>
      <div class="kpi-row">
        {kpi_card(f"{n_before:,}", "Total Record Sumber", f"OSS {n_oss:,} + CEISA {n_ceisa:,}", C['neutral'])}
        {kpi_card(f"{n_golden:,}", "Golden Record", f"Reduksi {pct_reduction:.1f}%", C['golden'])}
        {kpi_card(f"{overall_oss:.1f} / {overall_ceisa:.1f}", "DQ Overall Before", "OSS / CEISA (skala 0-100)", C['oss'])}
        {kpi_card(f"{overall_golden:.1f}", "DQ Overall After", "Golden Record (skala 0-100)", C['golden'])}
        {kpi_card(f"{n_out_of_sync:,}", "Sync Conflict", "IS_OUT_OF_SYNC = True", C['bad'])}
        {kpi_card(f"{n_high_sync_lag:,}", "High Sync Lag", "TGL_SYNC_OSS &gt; 30 hari", C['warn'])}
      </div>
      <p style="max-width:780px;margin:0 auto;color:#64748B;">
        Laporan ini merangkum seluruh hasil pipeline MDM (Tahap 0&ndash;6: Simulasi, Profiling, Cleansing &amp;
        Standardization, Duplicate Detection &amp; Matching, Golden Record &amp; Survivorship, Data Quality
        Monitoring, dan Profiling Dashboard), digabungkan dengan dokumentasi logika bisnis di
        <code>docs/</code>. Setiap section di bawah ini didesain sebagai satu "slide" sehingga laporan ini
        dapat langsung digunakan sebagai bahan presentasi (cetak ke PDF untuk mode slide).
      </p>
      <p style="max-width:780px;margin:8px auto 0 auto;color:#64748B;">
        Laporan ini juga berfungsi sebagai <b>prototipe/proof-of-concept</b>: secara teknis, MDM untuk data
        importir &amp; eksportir DJBC sangat memungkinkan untuk dibangun (lihat juga §21, integrasi API) &mdash;
        tantangan utamanya justru pada <b>tata kelola (governance)</b>, lihat §22.
      </p>
      <p style="max-width:780px;margin:18px auto 0 auto;color:#94A3B8;font-size:.85rem;">
        <b>Anggota Kelompok 5:</b> <i>(daftar nama menyusul)</i>
      </p>
    </div>
    """
    slides.append(dict(id='cover', cls='', kicker='', title='', body=cover_body))

    # --- §1, §2 (konteks bisnis, langsung dari docs) ----------------------
    slides.append(dict(id='s01', kicker='Konteks Bisnis', title='1. Judul &amp; Konteks Project', body=sec[1]))
    s02_body = sec[2] + """
    <p>Framing "OSS = System of Record untuk field legalitas, CEISA = data mart dengan snapshot historis" di atas
    konsisten dengan latar belakang bisnis project (lihat <code>docs/00_overview.md</code> &sect; Latar Belakang
    Bisnis, direproduksi lengkap di Lampiran C).</p>
    """
    slides.append(dict(id='s02', kicker='Konteks Bisnis', title='2. Latar Belakang Bisnis', body=s02_body))

    # --- §3 + data record counts -------------------------------------------
    s03_body = sec[3] + f"""
    <h2>📊 Data Aktual</h2>
    {fig_record_counts}
    <p>CEISA bersifat <i>data mart</i>: dari {n_ceisa:,} baris raw, terdapat <b>{n_dedup_removed:,}</b> baris
    snapshot duplikat (lihat audit trail Tahap 2) yang dibuang sebelum proses matching, sehingga jumlah CEISA
    yang dipakai untuk matching adalah <b>{n_ceisa_clean:,}</b> baris (1 baris/NIB).</p>
    """
    slides.append(dict(id='s03', kicker='Sumber Data', title='3. Dua Sumber Data: Peran &amp; Karakteristik', body=s03_body))

    slides.append(dict(id='s04', kicker='Sumber Data', title='4. Skema Data — OSS (16 Kolom)', body=sec[4]))
    slides.append(dict(id='s05', kicker='Sumber Data', title='5. Skema Data — CEISA (16 Kolom)', body=sec[5]))
    slides.append(dict(id='s06', kicker='Sumber Data', title='6. Pemetaan Kolom OSS ↔ CEISA', body=sec[6]))

    # --- §7 ------------------------------------------------------------------
    s07_body = sec[7] + """
    <div class="callout">
      <p>📊 <b>Catatan Implementasi</b></p>
      <p>Pipeline Tahap 5 (<code>dq_scorecard.csv</code>) secara aktual mengukur <b>5 dimensi</b>: 4 dimensi inti
      di atas (Completeness, Validity, Uniqueness, Timeliness) <b>+ Consistency</b> &mdash; yaitu kesesuaian nilai
      antar-field/antar-sumber (mis. <code>STATUS_NIB</code>, <code>KATEGORI</code>, <code>FLAG_EKSPOR</code> antara
      OSS dan CEISA), yang menjadi dasar flag <code>IS_OUT_OF_SYNC</code> dan
      <code>IS_LOGICAL_CONFLICT_NIPER</code> pada Golden Record (lihat §10).</p>
      <p>Laporan ini menambahkan dimensi ke-6, <b>Akurasi</b>, sebagai <i>placeholder</i> (lihat §17) agar gambaran
      6 dimensi DMBOK lebih lengkap secara presentasi. Penambahan ini murni di level laporan &mdash;
      <code>dq_scorecard.csv</code> dan <code>docs/02_business_rules.md</code> tidak diubah.</p>
    </div>
    """
    slides.append(dict(id='s07', kicker='Strategi &amp; Aturan MDM', title='7. Fondasi Logika Bisnis: 4 Dimensi Kualitas Data (DMBOK)', body=s07_body))

    # --- §8 + matching data ----------------------------------------------------
    n_fuzzy = int(cp_match_counts.get('FUZZY_REVIEW', 0))
    fuzzy_examples = candidate_pairs[candidate_pairs['match_type'] == 'FUZZY_REVIEW'].copy()
    nama_oss_map = df_oss.drop_duplicates('NIB').set_index(df_oss.drop_duplicates('NIB')['NIB'].astype(str))['NAMA_PERSEROAN']
    nama_ceisa_map = df_ceisa.drop_duplicates('ID_PERUSAHAAN').set_index('ID_PERUSAHAAN')['NAMA_PERUSAHAAN']
    fuzzy_examples['NAMA_OSS'] = fuzzy_examples['NIB_OSS'].astype(str).map(nama_oss_map)
    fuzzy_examples['NAMA_CEISA'] = fuzzy_examples['ID_PERUSAHAAN_CEISA'].map(nama_ceisa_map)
    fuzzy_display = fuzzy_examples[['NIB_OSS', 'NAMA_OSS', 'ID_PERUSAHAAN_CEISA', 'NAMA_CEISA', 'similarity_score']].rename(
        columns={'NIB_OSS': 'NIB (OSS)', 'NAMA_OSS': 'Nama Perusahaan (OSS)',
                 'ID_PERUSAHAAN_CEISA': 'ID Perusahaan (CEISA)', 'NAMA_CEISA': 'Nama Perusahaan (CEISA)',
                 'similarity_score': 'Skor Komposit'})
    fuzzy_table = simple_table(fuzzy_display, fmt={'Skor Komposit': '{:.2f}'.format})
    s08_body = sec[8] + f"""
    <h2>📊 Data Aktual</h2>
    <div class="grid-2">
      <div>{fig_match_type}</div>
      <div>{fig_duplicate_cluster}</div>
    </div>
    <p>Dari {len(candidate_pairs):,} kandidat pasangan, mayoritas ({cp_match_counts.get('EXACT_NIB', 0):,})
    cocok via <b>EXACT_NIB</b>, {cp_match_counts.get('EXACT_NPWP', 0):,} via <b>EXACT_NPWP</b> (skenario "NIB Typo" —
    lihat anomali #4), dan {n_fuzzy:,} via <b>FUZZY_REVIEW</b> (skenario "Fuzzy Identity / Typo Nama" — anomali #3).</p>
    <p>Skor komposit fuzzy = 0.20&times;kemiripan NPWP + 0.50&times;kemiripan Nama (Jaro-Winkler &amp; token-set-ratio)
    + 0.30&times;kemiripan Alamat. Klasifikasi: skor &ge; 0.85 &rarr; <code>FUZZY_MATCH</code> (otomatis valid),
    skor &lt; 0.70 &rarr; <code>NON_MATCH</code> (dibuang), dan <b>0.70 &le; skor &lt; 0.85 &rarr; <code>FUZZY_REVIEW</code></b>
    (perlu review manual — {n_fuzzy:,} contoh berikut). Kolom nama perusahaan ditampilkan untuk memperjelas seberapa
    mirip/berbeda kandidat di "zona abu-abu" ini:</p>
    {fuzzy_table}
    <p>Selain matching antar sumber, ditemukan <b>{n_clusters:,} cluster duplikat internal</b>
    ({dc_source_counts.get('OSS', 0):,} record OSS + {dc_source_counts.get('CEISA', 0):,} record CEISA) —
    skenario "Duplicate Entry" (anomali #9).</p>
    """
    slides.append(dict(id='s08', kicker='Strategi &amp; Aturan MDM', title='8. Strategi Matching Bertingkat (Tahap 3)', body=s08_body))

    # --- §9 + survivorship data --------------------------------------------------
    n_status_conflict = int(cl_field_counts.get('STATUS_NIB', 0))
    n_npwp_conflict = int(cl_field_counts.get('NPWP_VALUE', 0))
    n_nama_conflict = int(cl_field_counts.get('NAMA', 0))
    n_eksp_niper_conflict = int(cl_field_counts.get('FLAG_EKSPOR_vs_NIPER', 0))
    s09_body = sec[9] + f"""
    <h2>📊 Data Aktual</h2>
    <div class="grid-2">
      <div>{fig_golden_source}</div>
      <div>{fig_n_conflicts}</div>
    </div>
    {fig_provenance}
    <p>Grafik provenance di atas <b>membuktikan aturan survivorship benar-benar diterapkan</b>: field legalitas
    (NIB, NPWP, NAMA, ALAMAT, STATUS_NIB, JENIS_PERSEROAN, FLAG_IMPOR/EKSPOR) didominasi sumber <b>OSS</b>,
    sementara field operasional (KODE_KANTOR, NOMOR_TELPON, KATEGORI, NIPER, NOMOR_API, TGL_SYNC_OSS,
    TGL_TERBIT_NIB, ID_PERUSAHAAN) didominasi sumber <b>CEISA</b> — persis sesuai prinsip §9.A.</p>
    {fig_conflict_field}
    <p>Total <b>{len(conflict_log):,} konflik nilai</b> tercatat di <code>conflict_log.csv</code>, seluruhnya
    dimenangkan OSS sesuai aturan survivorship: <b>{n_npwp_conflict:,}</b> konflik format NPWP,
    <b>{n_nama_conflict:,}</b> konflik penulisan NAMA, <b>{n_status_conflict:,}</b> konflik STATUS_NIB
    (Sync Conflict), dan <b>{n_eksp_niper_conflict:,}</b> Logical Conflict FLAG_EKSPOR vs NIPER.</p>
    """
    slides.append(dict(id='s09', kicker='Strategi &amp; Aturan MDM', title='9. Aturan Survivorship — "Siapa yang Menang?" (Tahap 4)', body=s09_body))

    # --- §10 + risk flags ---------------------------------------------------------
    s10_body = sec[10] + f"""
    <h2>📊 Data Aktual</h2>
    {fig_risk_flags}
    <ul>
      <li><b>IS_OUT_OF_SYNC</b>: {n_out_of_sync:,} record ({n_out_of_sync/n_golden*100:.2f}%) — STATUS_NIB OSS
        berbeda dari CEISA, berisiko transaksi kepabeanan dengan entitas yang status legalnya sudah berubah.</li>
      <li><b>IS_STALE</b>: {n_stale:,} record ({n_stale/n_golden*100:.2f}%) — TGL_PERUBAHAN_NIB OSS sudah &gt;1 tahun.</li>
      <li><b>HIGH_SYNC_LAG</b>: {n_high_sync_lag:,} record ({n_high_sync_lag/n_golden*100:.2f}%) — TGL_SYNC_OSS
        CEISA sudah &gt;30 hari, melampaui SLA sinkronisasi bulanan.</li>
    </ul>
    """
    slides.append(dict(id='s10', kicker='Strategi &amp; Aturan MDM', title='10. Penandaan Konflik &amp; Risiko (Flag Bisnis Utama)', body=s10_body))

    # --- §11 + tabel anomali aktual --------------------------------------------------
    anomaly_rows = [
        ("1", "Stale Data", "TGL_PERUBAHAN_NIB OSS sangat lama (&gt;1 tahun)", "Tahap 1/5 — IS_STALE",
         f"OSS (before): {stale_oss_before:,}/{n_oss:,} ({stale_oss_before/n_oss*100:.1f}%) gagal rule TIME-IS_STALE.<br>"
         f"Golden (after): {n_stale:,}/{n_golden:,} ({n_stale/n_golden*100:.1f}%) record IS_STALE=True."),
        ("2", "Inconsistent NPWP", "CEISA mengirim NPWP tanpa titik/strip", "Tahap 2 — Standardisasi format",
         f"CEISA (before): {npwp_invalid_ceisa_before:,}/{n_ceisa:,} ({npwp_invalid_ceisa_before/n_ceisa*100:.1f}%) gagal VAL-NPWP-FORMAT "
         f"({npwp_ceisa:.1f}% valid).<br>Golden (after): {npwp_invalid_golden:,}/{n_golden:,} "
         f"({npwp_golden:.2f}% valid) — {len(flagged):,} record CEISA ({flag_pct_ceisa:.1f}%) ditandai "
         f"<code>FORMAT_NPWP_TIDAK_BAKU</code> di flagged_for_review.csv."),
        ("3", "Fuzzy Identity / Typo Nama", 'Nama perusahaan mirip, ada "(TYPO)" / beda spasi', "Tahap 3 — Fuzzy Matching",
         f"{n_fuzzy:,} pasangan candidate_pairs masuk zona <code>FUZZY_REVIEW</code> (skor komposit 0.70&ndash;0.85, "
         f"lihat §8), dan {int(match_type_counts.get('FUZZY_REVIEW', 0)):,} di antaranya jadi Golden Record."),
        ("4", "NIB Typo", "Satu digit NIB beda antar sistem", "Tahap 2/3 — Standardisasi &amp; Secondary Matching via NPWP",
         f"Tahap 2: {nib_fix_oss:,} NIB OSS ({nib_fix_oss/n_oss*100:.1f}%) &amp; {nib_fix_ceisa:,} NIB CEISA "
         f"({nib_fix_ceisa/n_ceisa*100:.1f}%) di-standardisasi (pad/trim 13 digit).<br>"
         f"Tahap 3: {int(cp_match_counts.get('EXACT_NPWP', 0)):,} pasangan ter-resolve via EXACT_NPWP "
         f"({int(match_type_counts.get('EXACT_NPWP', 0)):,} masuk Golden Record)."),
        ("5", "Sync Conflict", "STATUS_NIB OSS = DICABUT, CEISA = AKTIF (atau sebaliknya)", "Tahap 4 — Survivorship (IS_OUT_OF_SYNC)",
         f"{n_out_of_sync:,}/{n_golden:,} record ({n_out_of_sync/n_golden*100:.2f}%) IS_OUT_OF_SYNC=True — "
         f"semua di-resolve dengan STATUS_NIB OSS (latest-date-wins)."),
        ("6", "Logical Conflict", "FLAG_EKSPOR=N tapi NIPER terisi di CEISA", "Tahap 5 — Consistency Validation",
         f"Golden (after): {n_logical_conflict:,}/{n_golden:,} ({n_logical_conflict/n_golden*100:.2f}%) "
         f"IS_LOGICAL_CONFLICT_NIPER=True (rule CONS-FLAG_EKSPOR-NIPER).<br>"
         f"CEISA (before): {kat_niper_fail:,}/{n_ceisa:,} ({kat_niper_fail/n_ceisa*100:.1f}%) gagal "
         f"rule CONS-KATEGORI-NIPER."),
        ("7", "Orphan Records", "Record hanya ada di OSS atau hanya di CEISA", "Tahap 4 — Golden Record SOURCE tracking",
         f"SOURCE=OSS_ONLY: {n_orphan_oss:,} record ({n_orphan_oss/n_golden*100:.1f}%); "
         f"SOURCE=CEISA_ONLY: {n_orphan_ceisa:,} record ({n_orphan_ceisa/n_golden*100:.1f}%). "
         f"Total orphan {n_orphan_oss+n_orphan_ceisa:,} dari {n_golden:,} Golden Record."),
        ("8", "Missing Optional Field", "KELURAHAN, KODE_POS, NOMOR_TELPON, dll kosong", "Tahap 1/5 — Completeness Profiling",
         "; ".join(f"{f}: {v:.1f}%" for f, v in optional_missing.items()) + " (semua field opsional, dibiarkan kosong sesuai aturan §14)."),
        ("9", "Duplicate Entry", "Satu perusahaan muncul 2x di sistem yang sama", "Tahap 3 — Duplicate Clustering",
         f"{n_clusters:,} cluster duplikat internal: {dc_source_counts.get('OSS', 0):,} record OSS "
         f"(rule UNIQ-NIB OSS n_fail={dup_oss:,}) + {dc_source_counts.get('CEISA', 0):,} record CEISA."),
        ("10", "Data Mart Snapshot Duplicate", "NIB sama, &gt;1 baris CEISA dengan TGL_SYNC_OSS berbeda", "Tahap 2 — Pre-matching Dedup (DEDUP_SNAPSHOT)",
         f"{n_dedup_removed:,} baris snapshot CEISA dibuang ({dedup_row['pct_affected']:.2f}% dari raw CEISA), "
         f"snapshot dengan TGL_SYNC_OSS terbaru dipertahankan."),
    ]
    rows_html = "".join(
        f"<tr><td>{n}</td><td><b>{name}</b></td><td>{ex}</td><td>{tahap}</td><td>{found}</td></tr>"
        for n, name, ex, tahap, found in anomaly_rows
    )
    s11_body = sec[11] + f"""
    <h2>📊 Hasil Aktual per Anomali</h2>
    <div class="table-wrap"><table class="dtable">
    <thead><tr><th>#</th><th>Anomali</th><th>Contoh Skenario</th><th>Diuji di</th><th>Temuan Aktual dari Pipeline</th></tr></thead>
    <tbody>{rows_html}</tbody></table></div>
    """
    slides.append(dict(id='s11', kicker='Strategi &amp; Aturan MDM', title='11. Anomali Bisnis yang Disimulasikan &amp; Diuji', body=s11_body))

    # --- §12 Pipeline overview -----------------------------------------------------
    slides.append(dict(id='s12', kicker='Pipeline &amp; Hasil per Tahap', title='12. Pipeline End-to-End — Tahap 0 s.d. 6', body=sec[12]))

    # --- §13 Tahap 1 Profiling ----------------------------------------------------
    s13_body = sec[13] + f"""
    <h2>📊 Hasil Profiling Awal (Before)</h2>
    <h3>OSS</h3>{dq_rules_table(dq_rules[dq_rules['dataset'] == 'OSS'])}
    <h3>CEISA</h3>{dq_rules_table(dq_rules[dq_rules['dataset'] == 'CEISA'])}
    <h3>Visualisasi Missing Value &amp; DQ Scorecard Awal</h3>
    <div class="grid-2">
      <img src="{b64_image('reports/missing_value_oss.png')}" alt="Missing value OSS">
      <img src="{b64_image('reports/missing_value_ceisa.png')}" alt="Missing value CEISA">
    </div>
    <div class="grid-2" style="margin-top:14px;">
      <img src="{b64_image('reports/dq_scorecard_oss_master.png')}" alt="DQ Scorecard OSS">
      <img src="{b64_image('reports/dq_scorecard_ceisa_operational.png')}" alt="DQ Scorecard CEISA">
    </div>
    <p class="linklist">Laporan profiling lengkap (ydata-profiling):
      <a href="profiling_before_oss.html" target="_blank">profiling_before_oss.html</a> ·
      <a href="profiling_before_ceisa.html" target="_blank">profiling_before_ceisa.html</a> ·
      <a href="profiling_before.html" target="_blank">profiling_before.html</a></p>
    """
    slides.append(dict(id='s13', kicker='Pipeline &amp; Hasil per Tahap', title='13. Tahap 1 — Profiling (Before)', body=s13_body))

    # --- §14 Tahap 2 Cleansing -----------------------------------------------------
    s14_body = sec[14] + f"""
    <h2>📊 Audit Trail Cleansing (audit_trail.csv)</h2>
    <h3>OSS</h3>{audit_table(audit_trail[audit_trail['dataset'] == 'OSS'])}
    <h3>CEISA</h3>{audit_table(audit_trail[audit_trail['dataset'] == 'CEISA'])}
    <h2>Flagged for Review (flagged_for_review.csv)</h2>
    <p>{len(flagged):,} record ({flag_pct_ceisa:.1f}% dari CEISA) ditandai untuk review manual,
    seluruhnya karena <code>FORMAT_NPWP_TIDAK_BAKU</code> — NPWP tidak diformat ulang paksa karena
    formatnya tidak baku (anomali "Inconsistent NPWP" sengaja dipertahankan sebagai catatan kualitas data,
    sesuai <code>docs/02_business_rules.md</code> §1).</p>
    <p>Hasil akhir cleansing: <code>oss_cleaned.csv</code> ({n_oss:,} baris), <code>ceisa_cleaned.csv</code>
    ({n_ceisa_clean:,} baris setelah dedup snapshot, dari {n_ceisa:,} baris raw), digabung menjadi
    <code>dataset_clean.csv</code> ({len(dataset_clean):,} baris) sebagai input Tahap 3.</p>
    """
    slides.append(dict(id='s14', kicker='Pipeline &amp; Hasil per Tahap', title='14. Tahap 2 — Cleansing &amp; Standardization', body=s14_body))

    # --- §15 Tahap 3 Matching --------------------------------------------------------
    s15_body = sec[15] + f"""
    <h2>📊 Hasil Matching &amp; Duplicate Detection</h2>
    <div class="grid-2">
      <div>{fig_match_type}</div>
      <img src="{b64_image('reports/composite_score_distribution.png')}" alt="Distribusi composite similarity score">
    </div>
    <p>Dari {n_oss:,} record OSS dan {n_ceisa_clean:,} record CEISA (setelah dedup snapshot), terbentuk
    <b>{int(match_type_counts.get('EXACT_NIB',0)) + int(match_type_counts.get('EXACT_NPWP',0)) + int(match_type_counts.get('FUZZY_REVIEW',0)):,}
    pasangan matched</b> menjadi {len(df_golden[df_golden['SOURCE']=='MATCHED']):,} Golden Record SOURCE=MATCHED,
    sisanya {n_orphan_oss + n_orphan_ceisa:,} menjadi orphan (OSS_ONLY/CEISA_ONLY).
    Selain itu, {n_clusters:,} cluster duplikat internal terdeteksi via clustering graph
    (<code>duplicate_cluster.csv</code>, {len(duplicate_cluster):,} baris).</p>
    """
    slides.append(dict(id='s15', kicker='Pipeline &amp; Hasil per Tahap', title='15. Tahap 3 — Duplicate Detection &amp; Matching', body=s15_body))

    # --- §16 Tahap 4 Golden Record ----------------------------------------------------
    s16_body = sec[16] + f"""
    <h2>📊 Komposisi &amp; Provenance Golden Record</h2>
    <div class="grid-2">
      <div>{fig_golden_source}</div>
      <div>{fig_n_conflicts}</div>
    </div>
    {fig_provenance}
    <p><code>golden_record.csv</code> berisi {n_golden:,} baris x {df_golden.shape[1]} kolom.
    Setiap keputusan sumber per field tercatat di <code>provenance_log.csv</code>
    ({len(provenance_log):,} baris). {n_conflicts_dist.get(0,0):,} record ({n_conflicts_dist.get(0,0)/n_golden*100:.1f}%)
    tidak punya konflik nilai sama sekali (N_CONFLICTS=0), sedangkan
    {(n_conflicts_dist.drop(0, errors='ignore')).sum():,} record memiliki minimal 1 konflik yang
    diresolusi otomatis sesuai aturan survivorship.</p>
    """
    slides.append(dict(id='s16', kicker='Pipeline &amp; Hasil per Tahap', title='16. Tahap 4 — Golden Record &amp; Survivorship', body=s16_body))

    # --- §17 Tahap 5 DQ Monitoring -----------------------------------------------------
    s17_body = sec[17] + f"""
    <h2>📊 DQ Scorecard — OSS vs CEISA vs Golden Record</h2>
    {fig_dq_scorecard}
    <div class="table-wrap">{simple_table(dqs_table_display, fmt={c: '{:.2f}'.format for c in dqs_table_display.columns if c != 'dimension'})}</div>
    <div class="callout">
      <p><b>Catatan atas DQ Scorecard di atas:</b></p>
      <ul>
        <li><b>* Akurasi (Accuracy)</b> adalah baris <b>placeholder</b> (nilai dummy 100 untuk OSS/CEISA/Golden, delta=0).
        DMBOK mendefinisikan Akurasi sebagai kesesuaian data dengan <i>sumber kebenaran eksternal</i>
        (mis. data resmi instansi terkait), yang tidak tersedia sebagai dataset rujukan dalam project ini —
        lihat juga §7. Baris <b>"Overall"</b> tetap dihitung dari 5 dimensi nyata
        (Completeness, Validity, Uniqueness, Consistency, Timeliness); Akurasi tidak memengaruhi skor Overall.</li>
        <li><b>Mengapa skor Consistency Golden Record
        ({dq_scorecard.loc[dq_scorecard['dimension']=='Consistency','golden_score'].iloc[0]:.2f}) lebih rendah dari OSS
        ({dq_scorecard.loc[dq_scorecard['dimension']=='Consistency','oss_score'].iloc[0]:.2f}) / CEISA
        ({dq_scorecard.loc[dq_scorecard['dimension']=='Consistency','ceisa_score'].iloc[0]:.2f})?</b>
        Ini <b>bukan regresi kualitas</b>. Skor Consistency Golden adalah rata-rata dari <b>4 rule</b>, sedangkan
        OSS dan CEISA masing-masing hanya dievaluasi dengan <b>1 rule</b>:
          <ul>
            <li>OSS &mdash; <code>CONS-FLAG_IMPOR-JENIS_API</code>: 100.00%</li>
            <li>CEISA &mdash; <code>CONS-KATEGORI-NIPER</code>: 94.76%</li>
            <li>Golden &mdash; <code>CONS-FLAG_IMPOR-JENIS_API</code>: 100.00%, <code>CONS-KATEGORI-NIPER</code>: 95.45%,
            <code>CONS-STATUS_NIB-SYNC</code>: 96.66%, <code>CONS-FLAG_EKSPOR-NIPER</code>: 63.83%</li>
          </ul>
        Dua rule terakhir (<code>CONS-STATUS_NIB-SYNC</code> dan <code>CONS-FLAG_EKSPOR-NIPER</code>) adalah rule
        <b>cross-source</b> yang baru bisa dihitung <i>setelah</i> OSS dan CEISA digabung menjadi Golden Record —
        keduanya menjadi dasar flag <code>IS_OUT_OF_SYNC</code> dan <code>IS_LOGICAL_CONFLICT_NIPER</code>
        (lihat anomali #6 &mdash; "Logical Conflict" di §11). Skor Consistency Golden yang lebih rendah berarti MDM
        <b>berhasil mengungkap konflik antar-sumber</b> yang sebelumnya tersembunyi saat OSS dan CEISA dievaluasi
        terpisah &mdash; ini justru salah satu nilai tambah utama proses MDM.</li>
        <li><b>Mengapa masih ada {npwp_invalid_golden:,} record Golden yang gagal <code>VAL-NPWP-FORMAT</code>
        (dan {int(dq_rules.query("dataset=='GOLDEN' and rule_id=='VAL-NIB-DUMMY'")['n_fail'].iloc[0]):,} gagal
        <code>VAL-NIB-DUMMY</code>)?</b>
        Seluruh {npwp_invalid_golden:,} kegagalan <code>VAL-NPWP-FORMAT</code> berasal dari record
        <code>SOURCE='CEISA_ONLY'</code> (orphan, <code>NIB</code> dummy <code>'{DUMMY_NIB}'</code>) dengan nilai
        NPWP yang <b>jumlah digitnya salah</b> (bukan sekadar kurang titik/strip), terdeteksi via flag
        <code>IS_NPWP_INVALID</code> pada <code>ceisa_cleaned.csv</code>. Demikian pula, kegagalan
        <code>VAL-NIB-DUMMY</code> didominasi oleh record OSS/CEISA bernilai <code>NIB</code> dummy yang tidak
        memiliki pasangan match. Keduanya adalah <b>masalah data sumber</b> yang tidak bisa diperbaiki lewat
        transformasi/standardisasi &mdash; perlu verifikasi ke sistem asal (terkait dengan keterbatasan Akurasi
        di atas).</li>
      </ul>
    </div>
    <h2>Quality Gate Report</h2>
    {gate_table(quality_gate)}
    <h2>DQ Rule Results — Golden Record</h2>
    {dq_rules_table(dq_rules[dq_rules['dataset'] == 'GOLDEN'])}
    """
    slides.append(dict(id='s17', kicker='Pipeline &amp; Hasil per Tahap', title='17. Tahap 5 — Data Quality Monitoring (DQ Scorecard)', body=s17_body))

    # --- §18 Tahap 6 Profiling Dashboard -------------------------------------------------
    comparison_rows = pd.DataFrame([
        {'Metrik': 'Jumlah Record', 'OSS (Before)': f"{n_oss:,}", 'CEISA (Before)': f"{n_ceisa:,}", 'Golden Record (After)': f"{n_golden:,}"},
        {'Metrik': 'Missing Value % (field wajib)', 'OSS (Before)': f"{miss_oss:.2f}%", 'CEISA (Before)': f"{miss_ceisa:.2f}%", 'Golden Record (After)': f"{miss_golden:.2f}%"},
        {'Metrik': 'Validity NIB (13 digit)', 'OSS (Before)': f"{nib_oss:.2f}%", 'CEISA (Before)': f"{nib_ceisa:.2f}%", 'Golden Record (After)': f"{nib_golden:.2f}%"},
        {'Metrik': 'Validity NPWP (format baku)', 'OSS (Before)': f"{npwp_oss:.2f}%", 'CEISA (Before)': f"{npwp_ceisa:.2f}%", 'Golden Record (After)': f"{npwp_golden:.2f}%"},
        {'Metrik': 'Validity KODE_POS (5 digit)', 'OSS (Before)': f"{kp_oss:.2f}%", 'CEISA (Before)': f"{kp_ceisa:.2f}%", 'Golden Record (After)': f"{kp_golden:.2f}%"},
        {'Metrik': 'Duplikasi NIB (baris duplikat)', 'OSS (Before)': f"{dup_oss:,} ({dup_oss/n_oss*100:.2f}%)",
         'CEISA (Before)': f"{dup_ceisa:,} ({dup_ceisa/n_ceisa*100:.2f}%, data mart - expected)",
         'Golden Record (After)': f"{dup_golden_real:,} ({dup_golden_real/n_golden*100:.2f}%, di luar NIB dummy)"},
    ])
    s18_body = sec[18] + f"""
    <h2>📊 Perbandingan Before vs After</h2>
    {simple_table(comparison_rows)}
    {fig_format_validity}
    <div class="grid-2">
      <img src="{b64_image('reports/dq_comparison_oss.png')}" alt="DQ Comparison OSS">
      <img src="{b64_image('reports/dq_comparison_ceisa.png')}" alt="DQ Comparison CEISA">
    </div>
    <p class="linklist">Laporan profiling lengkap Golden Record (ydata-profiling):
      <a href="profiling_after.html" target="_blank">profiling_after.html</a></p>
    """
    slides.append(dict(id='s18', kicker='Pipeline &amp; Hasil per Tahap', title='18. Tahap 6 — Profiling Dashboard (After)', body=s18_body))

    # --- §19 Insight & Rekomendasi ---------------------------------------------------------
    s19_body = f"""
    <div class="callout good">
      <b>1. Konsolidasi data</b> berhasil mengurangi <b>{n_before - n_golden:,} baris ({pct_reduction:.1f}%)</b>
      dari total record OSS+CEISA ({n_before:,}) menjadi <b>{n_golden:,} Golden Record</b>
      (Single Importer/Exporter View), terutama berkat dedup snapshot CEISA ({n_dedup_removed:,} baris)
      dan exact/fuzzy matching NIB &amp; NPWP (Tahap 3).
    </div>
    <div class="callout good">
      <b>2. Uniqueness NIB meningkat signifikan</b>: dari {(1 - dup_oss/n_oss)*100:.2f}% (OSS) /
      {(1 - dup_ceisa/n_ceisa)*100:.2f}% (CEISA) menjadi <b>{(1 - dup_golden_real/n_golden)*100:.2f}%</b>
      di Golden Record (di luar {n_dummy_nib:,} NIB dummy/invalid yang sengaja dipertahankan sebagai
      catatan kualitas data untuk verifikasi ulang).
    </div>
    <div class="callout warn">
      <b>3. Risiko kualitas data yang masih perlu ditindaklanjuti</b> meski sudah ada Golden Record:
      <ul>
        <li><b>{n_dummy_nib:,}</b> record memiliki NIB dummy/tidak valid (<code>{DUMMY_NIB}</code>) &rarr;
            perlu verifikasi ulang ke OSS.</li>
        <li><b>{n_out_of_sync:,}</b> record berstatus <i>Sync Conflict</i> (STATUS_NIB OSS vs CEISA berbeda,
            IS_OUT_OF_SYNC=True).</li>
        <li><b>{n_logical_conflict:,}</b> record memiliki <i>Logical Conflict</i> antara FLAG_EKSPOR dan NIPER.</li>
        <li><b>{n_high_sync_lag:,}</b> record memiliki HIGH_SYNC_LAG (CEISA belum sinkron &gt;30 hari dari OSS).</li>
        <li><b>{n_stale:,}</b> record IS_STALE (TGL_PERUBAHAN_NIB OSS &gt;1 tahun) &rarr; kemungkinan
            perusahaan tidak aktif/data usang.</li>
        <li><b>{n_orphan_oss + n_orphan_ceisa:,}</b> record orphan (hanya ada di salah satu sistem) &rarr;
            {n_orphan_oss:,} OSS_ONLY, {n_orphan_ceisa:,} CEISA_ONLY.</li>
      </ul>
    </div>
    <h2>Rekomendasi Implementasi Data Governance &amp; MDM</h2>
    <ol class="reco-list">
      <li><b>Auto-update CEISA via trigger dari OSS.</b> Saat ini {n_high_sync_lag:,}
        ({n_high_sync_lag/n_golden*100:.1f}%) record melampaui SLA sync 30 hari — begitu ada perubahan di OSS
        (status NIB, alamat, dll.), langsung dorong ke CEISA agar sync lag minimal.</li>
      <li><b>Validasi format di titik input</b> (OSS &amp; CEISA) untuk NIB/NPWP/KODE_POS, agar anomali format
        (mis. {len(flagged):,} record NPWP tidak baku di CEISA) tidak terbawa ke data mart/operasional.</li>
      <li><b>Jadikan OSS sebagai System of Record</b> untuk legalitas (NIB, status badan hukum, status NIB) —
        sudah diterapkan di survivorship Golden Record (terbukti dari grafik provenance §9), perlu
        diformalkan sebagai kebijakan data governance resmi DJBC.</li>
      <li><b>Bangun proses rekonsiliasi berkala</b> (mis. bulanan) untuk menyelesaikan
        {n_out_of_sync:,} Sync Conflict dan {n_logical_conflict:,} Logical Conflict (FLAG_EKSPOR vs NIPER)
        yang terdeteksi di Golden Record, serta verifikasi ulang {n_dummy_nib:,} record dengan NIB dummy.</li>
      <li><b>Jadwalkan re-running pipeline</b> profiling &rarr; cleansing &rarr; matching &rarr; golden record
        &rarr; DQ monitoring secara periodik agar <code>dq_scorecard.csv</code> dan laporan ini selalu
        mencerminkan kondisi data terkini.</li>
    </ol>
    <div class="callout">
      Rekomendasi di atas bersifat <b>operasional/teknis</b> dalam scope pipeline ini. Untuk pembahasan
      <b>tata kelola (governance)</b> yang lebih strategis &mdash; termasuk pertanyaan "siapa yang
      bertanggung jawab atas data master ini secara berkelanjutan?" di level Kemenkeu maupun nasional &mdash;
      lihat §22 (Tata Kelola &amp; Rekomendasi Strategis).
    </div>
    """
    slides.append(dict(id='s19', kicker='Insight &amp; Penutup', title='19. Insight Bisnis &amp; Rekomendasi Data Governance', body=s19_body))

    # --- §20 Ringkasan + Deliverables checklist ------------------------------------------------
    deliverables = [
        ("Dataset Bersih (oss_cleaned, ceisa_cleaned, dataset_clean)", "data/processed/*.csv",
         f"{len(dataset_clean):,} baris (OSS {n_oss:,} + CEISA {n_ceisa:,})"),
        ("Audit Trail", "reports/audit_trail.csv", f"{len(audit_trail):,} entri operasi cleansing"),
        ("Candidate Pairs (hasil matching)", "reports/candidate_pairs.csv", f"{len(candidate_pairs):,} pasangan kandidat"),
        ("Duplicate Cluster", "reports/duplicate_cluster.csv", f"{len(duplicate_cluster):,} baris, {n_clusters:,} cluster"),
        ("Golden Record", "data/golden/golden_record.csv", f"{n_golden:,} baris x {df_golden.shape[1]} kolom"),
        ("Provenance Log", "reports/provenance_log.csv", f"{len(provenance_log):,} baris"),
        ("Conflict Log", "reports/conflict_log.csv", f"{len(conflict_log):,} baris"),
        ("DQ Scorecard (Tahap 5)", "reports/dq_scorecard.csv", "5 dimensi DMBOK x 3 dataset (OSS/CEISA/Golden)"),
        ("DQ Rule Results &amp; Quality Gate", "reports/dq_rule_results.csv, reports/quality_gate_report.csv",
         f"{len(dq_rules):,} rule, {len(quality_gate):,} gate"),
        ("Profiling Before (ydata-profiling)", "reports/profiling_before_oss.html, profiling_before_ceisa.html", "Tahap 1"),
        ("Profiling After (ydata-profiling)", "reports/profiling_after.html", "Tahap 6"),
        ("Bahan Presentasi (PPT/PDF, maks. 10 slide)",
         "reports/final_report.html, reports/final_report/index.html",
         "Dua format: reports/final_report.html (single-page, cetak ke PDF/PPT untuk presentasi) dan "
         "reports/final_report/index.html (multi-page, untuk browsing interaktif per section)"),
    ]
    deliv_rows = "".join(
        f"<tr><td>{name}</td><td><code>{path}</code></td><td class='deliv-status-ok'>✅ {info}</td></tr>"
        for name, path, info in deliverables
    )
    s20_body = sec[20] + f"""
    <h2>📋 Checklist Deliverable (sesuai Pedoman Mini Project, di luar notebook .ipynb)</h2>
    <div class="table-wrap"><table class="dtable">
    <thead><tr><th>Deliverable</th><th>File</th><th>Status &amp; Ringkasan</th></tr></thead>
    <tbody>{deliv_rows}</tbody></table></div>
    <p style="margin-top:18px;color:#94A3B8;font-size:.85rem;">
      Laporan dibuat otomatis oleh <code>Source/step11_final_report.py</code> &mdash;
      {datetime.now().strftime('%d %B %Y, %H:%M:%S')}.
    </p>
    """
    slides.append(dict(id='s20', kicker='Insight &amp; Penutup', title='20. Ringkasan Penutup &amp; Deliverables', body=s20_body))

    # --- §21 (Bonus) Integrasi API ---------------------------------------------------------
    s21_body = f"""
    <div class="callout warn">
      <b>Bagian opsional/bonus.</b> Section ini <b>di luar Tahap 1&ndash;6</b> PEDOMAN Mini Project
      (lihat <code>docs/00_overview.md</code> baris 39, Lampiran C) dan <b>tidak termasuk deliverable wajib</b>.
      Konten di bawah ini bersifat <b>konseptual/ilustratif</b>, diadaptasi dari Lab 5
      &mdash; "API &amp; Data Integration" (<code>reference/Data Profiling (1).ipynb</code>), untuk
      menggambarkan bagaimana <code>golden_record.csv</code> ({n_golden:,} baris) dapat dikonsumsi
      sebagai layanan oleh sistem lain.
    </div>

    <h2>Arsitektur: MDM Hub sebagai Service</h2>
    <pre><code>data/golden/golden_record.csv ──▶ MDM Hub API (FastAPI) ──▶ ngrok tunnel (publik, demo)
                                            │
                ┌───────────────┬───────────┼───────────────┬───────────────┐
                ▼               ▼           ▼               ▼               ▼
            GET /        GET /api/mdm/  GET /api/mdm/  GET /api/mdm/   POST /api/mdm/
          (health check)   {{nib}}        search?nama=   list?page=      validate
                                            │
                                            ▼
                                     GET /api/mdm/stats</code></pre>
    <p>Pola arsitektur ini sejalan dengan Lab 5 (FastAPI + Pydantic schema + ngrok tunnel + nest_asyncio),
    hanya domainnya diganti dari "Wajib Pajak / NPWP" menjadi "Importir-Eksportir / NIB" sesuai
    <code>golden_record.csv</code> hasil Tahap 4.</p>

    <h2>Endpoint MDM Hub API (konseptual)</h2>
    <div class="table-wrap"><table class="dtable">
    <thead><tr><th>Endpoint</th><th>Method</th><th>Deskripsi</th></tr></thead>
    <tbody>
      <tr><td><code>/</code></td><td>GET</td><td>Health check &mdash; status service &amp; jumlah total record.</td></tr>
      <tr><td><code>/api/mdm/{{nib}}</code></td><td>GET</td><td>Ambil 1 Golden Record berdasarkan <code>NIB</code>.</td></tr>
      <tr><td><code>/api/mdm/search?nama=</code></td><td>GET</td><td>Cari Golden Record berdasarkan kemiripan <code>NAMA</code> (fuzzy search).</td></tr>
      <tr><td><code>/api/mdm/list?page=</code></td><td>GET</td><td>Daftar Golden Record dengan pagination.</td></tr>
      <tr><td><code>/api/mdm/validate</code></td><td>POST</td><td>Validasi data NIB/NPWP/Nama dari sistem eksternal terhadap MDM (mis. cek <code>VAL-NIB-DUMMY</code>/<code>VAL-NPWP-FORMAT</code>) sebelum diproses.</td></tr>
      <tr><td><code>/api/mdm/stats</code></td><td>GET</td><td>Statistik ringkas MDM Hub (jumlah record, distribusi <code>SOURCE</code>, skor DQ Scorecard &mdash; lihat §17).</td></tr>
    </tbody></table></div>

    <h2>Sinkronisasi Event-Driven (Webhook)</h2>
    <p><code>docs/00_overview.md</code> baris 24 mencatat sebagai <i>next step</i> di luar scope:
    "idealnya ada mekanisme <b>auto-update CEISA via trigger</b> dari OSS agar sync lag ke depan minim"
    &mdash; terkait langsung dengan <code>HIGH_SYNC_LAG</code>/<code>IS_OUT_OF_SYNC</code> yang dibahas di
    §19 (Insight &amp; Rekomendasi). Lab 5 mengilustrasikan mekanisme ini lewat pola
    <code>WebhookEvent</code> &amp; <code>WebhookBroker</code>:</p>
    <pre><code>WebhookEvent(
    event_id      = "evt-00123",
    event_type    = "DATA_UPDATED",   # DATA_CREATED | DATA_UPDATED | DATA_DELETED
    entity_type   = "GOLDEN_RECORD",
    nib           = "1234567890123",
    changed_fields= ["STATUS_NIB"],
    old_values    = {{"STATUS_NIB": "AKTIF"}},
    new_values    = {{"STATUS_NIB": "NONAKTIF"}},
    timestamp     = "2026-06-12T10:00:00",
    source        = "OSS",
)</code></pre>
    <p>Konsepnya: setiap kali <code>STATUS_NIB</code>/<code>KATEGORI</code>/<code>FLAG_EKSPOR</code> berubah
    di OSS, MDM Hub <b>publish</b> event <code>WebhookEvent</code> ke subscriber (mis. CEISA, sistem internal
    DJBC lain) sehingga update OSS ter-propagate tanpa menunggu sync batch &mdash; mengurangi
    <code>HIGH_SYNC_LAG</code> ({n_high_sync_lag:,} record saat ini, lihat §10/§19) dan
    <code>IS_OUT_OF_SYNC</code> ({n_out_of_sync:,} record).</p>

    <div class="callout warn">
      <b>Disclaimer:</b> Seluruh API, endpoint, dan webhook di atas adalah <b>desain konseptual</b> untuk
      ilustrasi &mdash; tidak diimplementasikan/dijalankan sebagai bagian dari deliverable Tahap 0&ndash;6
      project ini.
    </div>
    """
    slides.append(dict(id='s21', kicker='Insight &amp; Penutup', title='21. (Bonus) Integrasi API — MDM Hub sebagai Service', body=s21_body))

    # --- §22 Tata Kelola & Rekomendasi Strategis -------------------------------------------------
    s22_body = """
    <div class="callout">
      <p>Pipeline Tahap 0&ndash;6 dan integrasi API konseptual di §21 menunjukkan bahwa secara <b>teknis</b>,
      MDM untuk data importir/eksportir DJBC <b>sangat memungkinkan</b> untuk dibangun. Laporan ini pada
      dasarnya adalah <b>prototipe / proof-of-concept</b> &mdash; tantangan sesungguhnya bukan pada teknologi,
      melainkan pada <b>tata kelola (governance)</b>.</p>
      <p>Dan semakin <b>makro</b> skala penerapannya, semakin besar dampaknya: pada level unit setingkat
      <b>Eselon I</b> saja, MDM yang dapat dipercaya sudah berpengaruh signifikan terhadap kualitas
      keputusan &mdash; apalagi bila diterapkan lintas Kementerian/Lembaga atau di level <b>nasional</b>.</p>
    </div>

    <h2>Temuan Utama</h2>
    <p>Masalah data di DJBC <b>bukan semata teknikal</b> &mdash; akarnya adalah <b>tidak ada pihak yang secara
    eksplisit bertanggung jawab</b> memastikan data master tetap akurat sepanjang waktu.</p>

    <h2>Level Makro &mdash; Kajian Master Data Nasional</h2>
    <ul>
      <li>Untuk entitas <b>individu</b>, <b>NIK (Dukcapil)</b> sudah berfungsi sebagai <i>de facto</i> master
      identifier penduduk.</li>
      <li>Untuk entitas <b>badan usaha</b>, belum ada master yang jelas &mdash; ada tiga kandidat yang perlu
      dikaji lebih lanjut:
        <ul>
          <li><b>NIB</b> (OSS-BKPM, domain perizinan)</li>
          <li><b>NPWP</b> (DJP, domain perpajakan)</li>
          <li>Data <b>Ditjen AHU</b> (domain legalitas badan hukum)</li>
        </ul>
      </li>
      <li>Masing-masing kandidat punya kekuatan di domainnya masing-masing, tapi juga keterbatasan &mdash;
      kajian lebih lanjut diperlukan untuk menentukan mana yang paling layak menjadi sumber master
      lintas K/L.</li>
      <li><b>Satu Data Indonesia</b> (Perpres 39/2019) idealnya diperkuat mandatnya ke layer ini.</li>
    </ul>

    <h2>Level Mikro &mdash; Gap Konkret di DJBC</h2>
    <ul>
      <li>Data badan usaha dari OSS dapat diduga sudah divalidasi saat <i>onboarding</i>, tetapi tidak ada
      kewajiban pembaruan berkala &mdash; data berpotensi <i>stale</i> tanpa ada yang mendeteksi (lihat
      <code>HIGH_SYNC_LAG</code>/<code>IS_OUT_OF_SYNC</code> di §10/§19).</li>
      <li>Kementerian Keuangan perlu membangun <b>MDM internal</b> yang mengambil data dari sumber master
      nasional dan memperkayanya dengan atribut domain Kemenkeu (mis. status kepabeanan, NIPER, dsb).</li>
    </ul>

    <h2>Prinsip Tata Kelola (DMBOK Ch. 10)</h2>
    <ul>
      <li>Setiap atribut di MDM harus punya <b>Data Steward</b> yang bertanggung jawab atas definisi,
      standar kualitas, dan eskalasi anomali &mdash; bukan cukup ada sistemnya, harus ada <b>orangnya</b>.</li>
      <li><b>MDM bukan soal tools-nya; MDM adalah disiplin.</b> Tanpa governance yang jelas, sistem
      secanggih apapun tidak menjamin kebenaran datanya.</li>
    </ul>
    """
    slides.append(dict(id='s22', kicker='Insight &amp; Penutup', title='22. Tata Kelola &amp; Rekomendasi Strategis', body=s22_body))

    # --- Lampiran -----------------------------------------------------------------------------
    slides.append(dict(id='appendix-dict', kicker='Lampiran', title='Lampiran A — Data Dictionary (OSS vs CEISA)', body=doc01))
    slides.append(dict(id='appendix-rules', kicker='Lampiran', title='Lampiran B — Business Rules &amp; DMBOK', body=doc02))
    slides.append(dict(id='appendix-overview', kicker='Lampiran', title='Lampiran C — Overview &amp; Roadmap Project', body=doc00))

    # --- Lampiran D — Data Viewer (CSV) -------------------------------------------------------
    csv_data_json = json.dumps({key: csv_b64(path) for key, (label, path) in CSV_FILES.items()})
    csv_meta_json = json.dumps({key: dict(label=label, path=path) for key, (label, path) in CSV_FILES.items()})
    csv_tabs_html = "".join(
        f'<button class="csv-tab{" active" if key == "golden_record" else ""}" data-key="{key}" '
        f'onclick="switchCsv(\'{key}\')">{label}</button>'
        for key, (label, path) in CSV_FILES.items()
    )

    appendix_data_head = f"""
    <div class="callout">
      <p>Tabel di bawah ini menampilkan <b>seluruh isi CSV hasil pipeline</b> (Tahap 0&ndash;6) secara interaktif
      &mdash; data di-<i>embed</i> langsung di dalam file HTML ini (base64), sehingga bisa dibuka dan diperiksa
      tanpa software tambahan. Gunakan tab di bawah untuk memilih dataset, kotak pencarian untuk memfilter
      seluruh kolom, dan tombol navigasi untuk pindah halaman ({CSV_PAGE_SIZE} baris/halaman).</p>
    </div>
    <div class="csv-tabs">{csv_tabs_html}</div>
    <div class="csv-viewer-toolbar">
      <div id="csv-viewer-info"></div>
      <input type="text" id="csv-search-input" class="csv-search" placeholder="Cari di semua kolom..." oninput="csvSearch(this.value)">
    </div>
    <div id="csv-viewer-table"></div>
    """

    appendix_data_js = """
    <script>
    const CSV_DATA = __CSV_DATA__;
    const CSV_META = __CSV_META__;
    const CSV_PAGE_SIZE = __CSV_PAGE_SIZE__;
    const csvCache = {};
    let csvActive = null;

    function b64ToUtf8(b64) {
      const bin = atob(b64);
      const bytes = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      return new TextDecoder('utf-8').decode(bytes);
    }

    function parseCsv(text) {
      const rows = [];
      let row = [], field = '', inQuotes = false;
      for (let i = 0; i < text.length; i++) {
        const c = text[i];
        if (inQuotes) {
          if (c === '"') {
            if (text[i + 1] === '"') { field += '"'; i++; }
            else inQuotes = false;
          } else field += c;
        } else if (c === '"') inQuotes = true;
        else if (c === ',') { row.push(field); field = ''; }
        else if (c === '\\n') { row.push(field); rows.push(row); row = []; field = ''; }
        else if (c === '\\r') { /* ignore */ }
        else field += c;
      }
      if (field.length || row.length) { row.push(field); rows.push(row); }
      while (rows.length && rows[rows.length - 1].length === 1 && rows[rows.length - 1][0] === '') rows.pop();
      return rows;
    }

    function escapeHtml(s) {
      return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function loadCsv(key) {
      if (!csvCache[key]) {
        const rows = parseCsv(b64ToUtf8(CSV_DATA[key]));
        csvCache[key] = { header: rows[0] || [], data: rows.slice(1), filtered: rows.slice(1), page: 0, search: '' };
      }
      return csvCache[key];
    }

    function switchCsv(key) {
      csvActive = key;
      document.querySelectorAll('.csv-tab').forEach(function (b) {
        b.classList.toggle('active', b.dataset.key === key);
      });
      const state = loadCsv(key);
      document.getElementById('csv-search-input').value = state.search || '';
      renderCsvTable();
    }

    function renderCsvTable() {
      const key = csvActive;
      const state = csvCache[key];
      const meta = CSV_META[key];
      const totalPages = Math.max(1, Math.ceil(state.filtered.length / CSV_PAGE_SIZE));
      state.page = Math.min(state.page, totalPages - 1);
      const start = state.page * CSV_PAGE_SIZE;
      const pageRows = state.filtered.slice(start, start + CSV_PAGE_SIZE);

      document.getElementById('csv-viewer-info').innerHTML =
        '<b>' + escapeHtml(meta.label) + '</b> &mdash; <code>' + escapeHtml(meta.path) + '</code> (' +
        state.data.length.toLocaleString('id-ID') + ' baris x ' + state.header.length + ' kolom)';

      let html = '<div class="table-wrap"><table class="dtable"><thead><tr>';
      state.header.forEach(function (h) { html += '<th>' + escapeHtml(h) + '</th>'; });
      html += '</tr></thead><tbody>';
      pageRows.forEach(function (r) {
        html += '<tr>';
        r.forEach(function (c) { html += '<td>' + escapeHtml(c) + '</td>'; });
        html += '</tr>';
      });
      html += '</tbody></table></div>';
      html += '<div class="csv-pagination">' +
        '<button onclick="csvPage(-1)"' + (state.page <= 0 ? ' disabled' : '') + '>&larr; Sebelumnya</button>' +
        '<span>Halaman ' + (state.page + 1) + ' / ' + totalPages + ' &middot; ' +
        state.filtered.length.toLocaleString('id-ID') + ' baris' + (state.search ? ' (hasil pencarian)' : '') + '</span>' +
        '<button onclick="csvPage(1)"' + (state.page >= totalPages - 1 ? ' disabled' : '') + '>Berikutnya &rarr;</button>' +
        '</div>';
      document.getElementById('csv-viewer-table').innerHTML = html;
    }

    function csvSearch(term) {
      const state = csvCache[csvActive];
      state.search = term;
      const q = term.trim().toLowerCase();
      state.filtered = q ? state.data.filter(function (r) {
        return r.some(function (c) { return c.toLowerCase().includes(q); });
      }) : state.data;
      state.page = 0;
      renderCsvTable();
    }

    function csvPage(delta) {
      const state = csvCache[csvActive];
      state.page += delta;
      renderCsvTable();
    }

    document.addEventListener('DOMContentLoaded', function () { switchCsv('golden_record'); });
    </script>
    """
    appendix_data_js = (appendix_data_js
                         .replace('__CSV_DATA__', csv_data_json)
                         .replace('__CSV_META__', csv_meta_json)
                         .replace('__CSV_PAGE_SIZE__', str(CSV_PAGE_SIZE)))

    appendix_data_body = appendix_data_head + appendix_data_js
    slides.append(dict(id='appendix-data', kicker='Lampiran', title='Lampiran D — Data Viewer (CSV Hasil)', body=appendix_data_body))

    # -----------------------------------------------------------------
    # Navigasi
    # -----------------------------------------------------------------
    nav_groups = [
        dict(label='Ringkasan', links=[('cover', 'Cover & KPI')]),
        dict(label='Konteks Bisnis', links=[('s01', '1. Judul & Konteks'), ('s02', '2. Latar Belakang')]),
        dict(label='Sumber Data', links=[('s03', '3. OSS vs CEISA'), ('s04', '4. Skema OSS'),
                                          ('s05', '5. Skema CEISA'), ('s06', '6. Pemetaan Kolom')]),
        dict(label='Strategi & Aturan MDM', links=[('s07', '7. Dimensi DMBOK'), ('s08', '8. Strategi Matching'),
                                                     ('s09', '9. Survivorship'), ('s10', '10. Konflik & Risiko'),
                                                     ('s11', '11. Anomali Bisnis')]),
        dict(label='Pipeline & Hasil', links=[('s12', '12. Pipeline E2E'), ('s13', '13. Tahap 1 Profiling'),
                                               ('s14', '14. Tahap 2 Cleansing'), ('s15', '15. Tahap 3 Matching'),
                                               ('s16', '16. Tahap 4 Golden Record'), ('s17', '17. Tahap 5 DQ Monitoring'),
                                               ('s18', '18. Tahap 6 Profiling Dashboard')]),
        dict(label='Insight & Penutup', links=[('s19', '19. Insight & Rekomendasi'), ('s20', '20. Penutup & Deliverables'),
                                                ('s21', '21. (Bonus) Integrasi API'), ('s22', '22. Tata Kelola & Rekomendasi')]),
        dict(label='Lampiran', links=[('appendix-dict', 'A. Data Dictionary'), ('appendix-rules', 'B. Business Rules'),
                                       ('appendix-overview', 'C. Overview & Roadmap'), ('appendix-data', 'D. Data Viewer (CSV)')]),
    ]

    report_title = 'Laporan Akhir MDM DJBC — Single Importer & Exporter View'

    print("Menulis reports/final_report.html (single-page)...")
    html = TEMPLATE.render(title=report_title, css=CSS, plotlyjs=PLOTLY_JS,
                            nav_groups=nav_groups, slides=slides)
    out_path = REPORTS / 'final_report.html'
    out_path.write_text(html, encoding='utf-8')
    print(f"✅ Laporan akhir (single-page) berhasil dibuat: {out_path} ({out_path.stat().st_size/1024:.1f} KB)")

    # -----------------------------------------------------------------
    # Output multi-page: reports/final_report/
    # -----------------------------------------------------------------
    print("Menulis reports/final_report/ (multi-page)...")
    site_dir = REPORTS / 'final_report'
    assets_dir = site_dir / 'assets'
    assets_dir.mkdir(parents=True, exist_ok=True)
    (assets_dir / 'style.css').write_text(CSS, encoding='utf-8')
    (assets_dir / 'plotly.min.js').write_text(PLOTLY_JS, encoding='utf-8')

    flat_nav = [(sid, stitle) for group in nav_groups for sid, stitle in group['links']]

    def nav_href(sid):
        return 'index.html' if sid == 'cover' else f'{sid}.html'

    index_html = INDEX_TEMPLATE.render(title=report_title, nav_groups=nav_groups, cover_body=cover_body, active_id='cover')
    (site_dir / 'index.html').write_text(index_html, encoding='utf-8')

    for slide in slides:
        if slide['id'] == 'cover':
            continue
        idx = next(i for i, (sid, _) in enumerate(flat_nav) if sid == slide['id'])
        prev_link = flat_nav[idx - 1] if idx > 0 else None
        next_link = flat_nav[idx + 1] if idx < len(flat_nav) - 1 else None
        prev = dict(href=nav_href(prev_link[0]), title=prev_link[1]) if prev_link else None
        next_ = dict(href=nav_href(next_link[0]), title=next_link[1]) if next_link else None
        page_html = PAGE_TEMPLATE.render(title=report_title, nav_groups=nav_groups, slide=slide,
                                          active_id=slide['id'], prev=prev, next=next_)
        (site_dir / f"{slide['id']}.html").write_text(page_html, encoding='utf-8')

    n_pages = len(slides)  # cover -> index.html + (n_pages - 1) section pages
    print(f"✅ Laporan akhir (multi-page) berhasil dibuat: {site_dir} ({n_pages} halaman)")
