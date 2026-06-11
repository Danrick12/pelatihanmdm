# ============================================================
# CELL 14: QUALITY GATE — PEMERIKSAAN OTOMATIS
# Semua gate harus PASS sebelum dataset diekspor
# ============================================================

class QualityGate:
    """Runner untuk quality gate checks."""
    def __init__(self, df):
        self.df      = df
        self.results = []
        self.all_pass= True

    def check(self, gate_name, condition_fn, threshold, description):
        """
        Jalankan satu quality gate.
        condition_fn: fungsi yang mengembalikan nilai (float/int)
        threshold: nilai minimum yang harus dipenuhi
        """
        try:
            value  = condition_fn(self.df)
            passed = value >= threshold
            status = '✅ PASS' if passed else '❌ FAIL'
            if not passed: self.all_pass = False
        except Exception as e:
            value  = -1
            passed = False
            status = f'💥 ERROR: {e}'
            self.all_pass = False

        self.results.append({
            'Gate'      : gate_name,
            'Deskripsi' : description,
            'Nilai'     : f'{value:.2f}' if isinstance(value, float) else str(value),
            'Threshold' : str(threshold),
            'Status'    : status,
        })
        print(f'   {status}  {gate_name:<30} | Nilai: {str(value):<10} | Min: {threshold}')

    def report(self):
        print('\n' + '='*70)
        verdict = '✅ SEMUA GATE PASSED — Dataset siap diekspor!' if self.all_pass \
                  else '❌ ADA GATE YANG GAGAL — Perbaiki sebelum export!'
        print(f'  HASIL QUALITY GATE: {verdict}')
        print('='*70)
        return pd.DataFrame(self.results)


# Inisialisasi dan jalankan quality gate
qg = QualityGate(df_clean)
print('🔍 MENJALANKAN QUALITY GATE...')
print('-'*70)

# Gate 1: Field kritis tidak boleh null
qg.check('NO_NULL_NPWP',
    lambda d: 100 - d['npwp'].isna().mean()*100, 100,
    'Completeness NPWP = 100%')

qg.check('NO_NULL_NAMA',
    lambda d: 100 - d['nama_wp'].isna().mean()*100, 100,
    'Completeness nama_wp = 100%')

qg.check('NO_NULL_JENIS',
    lambda d: 100 - d['jenis_wp'].isna().mean()*100, 100,
    'Completeness jenis_wp = 100%')

# Gate 2: Format NPWP minimal 90% valid
NPWP_PAT = r'^\d{2}\.\d{3}\.\d{3}\.\d{1}-\d{3}\.\d{3}$'
qg.check('NPWP_FORMAT_90PCT',
    lambda d: d['npwp'].str.match(NPWP_PAT).mean()*100, 90,
    'Format NPWP valid >= 90%')

# Gate 3: Status WP hanya nilai yang valid
valid_sw = ['Aktif','Non-Aktif','Hapus']
qg.check('STATUS_WP_VALID',
    lambda d: d['status_wp'].isin(valid_sw).mean()*100, 100,
    'Semua status_wp adalah nilai yang valid')

# Gate 4: Tidak ada exact duplicate pada NPWP + nama (setelah standardisasi)
qg.check('NO_EXACT_DUP',
    lambda d: 100 - d.duplicated(subset=['npwp','nama_wp']).mean()*100, 95,
    'Duplikat NPWP+Nama <= 5%')

# Gate 5: Kode provinsi terisi semua
qg.check('PROVINSI_COMPLETE',
    lambda d: 100 - d['kode_provinsi'].isna().mean()*100, 100,
    'Completeness kode_provinsi = 100%')

# Gate 6: Penghasilan tidak negatif
qg.check('PENGHASILAN_POSITIVE',
    lambda d: (d['penghasilan'] > 0).mean()*100, 99,
    'Penghasilan > 0 pada >= 99% record')

# Tampilkan hasil
gate_df = qg.report()
display(gate_df)
import pandas as pd
from datetime import datetime

# ============================================================
# CELL 15: EXPORT CLEAN DATASET & LAPORAN AUDIT TRAIL
# ============================================================

# ── Buat kolom metadata cleansing ──
df_clean['cleansed_at']      = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
df_clean['cleansing_version'] = 'LAB2_v1.0'

# ── Pilih kolom untuk clean dataset (hanya kolom cleansing yang dipertahankan) ──
# Kolom-kolom hasil cleansing yang akan dipertahankan dalam dataset final.
# Kolom original, helper, dan status akan dihapus.
# columns_to_keep = [
#     'id_record', 'npwp', 'nik', 'nama_wp', 'jenis_wp', 'status_wp',
#     'status_pkp', 'kode_kpp', 'nama_kpp', 'kode_provinsi', 'nama_provinsi',
#     'alamat', 'kelurahan', 'kota', 'kode_pos', 'klu_kode', 'klu_nama',
#     'email', 'telepon', 'penghasilan', 'tanggal_daftar', 'flag_review',
#     'kode_provinsi_clean', 'kode_kpp_clean', 'penghasilan_log',
#     'cleansed_at', 'cleansing_version'
# ]

columns_to_keep = [
    'id_record', 'npwp', 'nik', 'nama_wp', 'jenis_wp', 'status_wp',
    'status_pkp', 'kode_kpp', 'nama_kpp', 'kode_provinsi', 'nama_provinsi',
    'alamat', 'kelurahan', 'kota', 'kode_pos', 'klu_kode', 'klu_nama',
    'email', 'telepon', 'penghasilan', 'tanggal_daftar'
]
df_export = df_clean[columns_to_keep].copy()

# ── Export 1: Clean Dataset ──
df_export.to_csv('dataset_wp_clean.csv', index=False)
print(f'✅ Clean dataset disimpan: dataset_wp_clean.csv')
print(f'   Shape : {df_export.shape}')
print(f'   Kolom : {list(df_export.columns)}')

# ── Export 2: Audit Trail ──
audit_df = audit.to_dataframe()
audit_df.to_csv('audit_trail_lab2.csv', index=False)
print(f'\n✅ Audit trail disimpan: audit_trail_lab2.csv')
print(f'   Total operasi dicatat: {len(audit_df)}')

# ── Export 3: Flag Review (record perlu verifikasi manual) ──
review_df = df_clean[df_clean['flag_review'].notna()][
    ['id_record','npwp','nama_wp','jenis_wp','flag_review']
]
review_df.to_csv('flagged_records_lab2.csv', index=False)
print(f'\n✅ Flagged records disimpan: flagged_records_lab2.csv')
print(f'   Record perlu review: {len(review_df):,}')

# ── Tampilkan Audit Trail Summary ──
audit.summary()# ============================================================
# CELL 16: PERBANDINGAN DQ SCORE BEFORE vs AFTER CLEANSING
# ============================================================

# DQ Score SEBELUM (dari LAB 1, referensi manual)
dq_before = {
    'Completeness' : 97.5,
    'Validity'     : 89.0,
    'Uniqueness'   : 94.5,
    'Consistency'  : 85.0,
    'Timeliness'   : 99.8,
    'Accuracy'     : 100.0,
}

# DQ Score SESUDAH cleansing — hitung ulang
NPWP_PAT2  = r'^\d{2}\.\d{3}\.\d{3}\.\d{1}-\d{3}\.\d{3}$'
df_op_clean = df_clean[df_clean['jenis_wp']=='Orang Pribadi']

dq_after = {
    'Completeness' : (1 - df_clean[['npwp','nama_wp','jenis_wp',
                          'status_wp','kode_kpp','kode_provinsi']].isna().mean().mean()) * 100,
    'Validity'     : (df_clean['npwp'].str.match(NPWP_PAT2).mean()) * 100,
    'Uniqueness'   : (1 - df_clean.duplicated(subset=['npwp']).mean()) * 100,
    'Consistency'  : (1 - df_clean['nama_wp'].apply(
                          lambda x: str(x).isupper() or str(x).islower()
                          if pd.notna(x) else False).mean()) * 100,
    'Timeliness'   : (1 - (pd.to_datetime(df_clean['tanggal_daftar'],errors='coerce')
                          > pd.Timestamp.now()).mean()) * 100,
    'Accuracy'     : (df_clean['nama_provinsi'] == df_clean['kode_provinsi'].map(
                          PROVINSI_REF)).mean() * 100,
}

# Bobot dimensi
weights = {'Completeness':0.20,'Validity':0.25,'Uniqueness':0.20,
           'Consistency':0.15,'Timeliness':0.10,'Accuracy':0.10}

total_before = sum(dq_before[d]*weights[d] for d in weights)
total_after  = sum(dq_after[d] *weights[d] for d in weights)

# ── Print perbandingan ──
print('='*65)
print('  PERBANDINGAN DQ SCORE — BEFORE vs AFTER CLEANSING')
print('='*65)
print(f'{"Dimensi":<16} {"Before":>8}  {"After":>8}  {"Delta":>8}  Status')
print('-'*65)
for dim in weights:
    b   = dq_before[dim]
    a   = dq_after[dim]
    d   = a - b
    ico = '⬆' if d > 0 else ('⬇' if d < 0 else '=')
    print(f'{dim:<16} {b:>7.2f}%  {a:>7.2f}%  {ico}{abs(d):>6.2f}%')
print('='*65)
print(f'{"TOTAL DQ SCORE":<16} {total_before:>7.2f}%  {total_after:>7.2f}%  ⬆{total_after-total_before:.2f}%')
print('='*65)

# ── Visualisasi Before vs After ──
dims   = list(weights.keys())
before = [dq_before[d] for d in dims]
after  = [dq_after[d]  for d in dims]

fig, axes = plt.subplots(1, 2, figsize=(16, 6))
fig.suptitle('DQ Score: Before vs After Cleansing', fontsize=15, fontweight='bold')

# Chart 1: Grouped Bar
ax1  = axes[0]
x    = np.arange(len(dims))
w    = 0.35
ax1.bar(x-w/2, before, w, label='Before', color='#FF7043', alpha=0.85)
ax1.bar(x+w/2, after,  w, label='After',  color='#4CAF50', alpha=0.85)
ax1.set_xticks(x); ax1.set_xticklabels(dims, fontsize=9, rotation=15)
ax1.set_ylim(75, 105); ax1.set_ylabel('Score (%)')
ax1.axhline(y=95, color='navy', linestyle='--', alpha=0.5, linewidth=1.5)
ax1.legend(); ax1.set_title('DQ Score per Dimensi')
for i,(b,a) in enumerate(zip(before,after)):
    ax1.text(i-w/2, b+0.3, f'{b:.1f}', ha='center', fontsize=8)
    ax1.text(i+w/2, a+0.3, f'{a:.1f}', ha='center', fontsize=8, color='green', fontweight='bold')

# Chart 2: Delta improvement
ax2    = axes[1]
deltas = [a-b for a,b in zip(after,before)]
colors = ['#4CAF50' if d >= 0 else '#F44336' for d in deltas]
ax2.barh(dims, deltas, color=colors, edgecolor='white')
ax2.axvline(x=0, color='black', linewidth=0.8)
ax2.set_xlabel('Delta Score (%)')
ax2.set_title(f'Peningkatan per Dimensi\n(Total: +{total_after-total_before:.2f} poin)')
for i,d in enumerate(deltas):
    ax2.text(d+0.1 if d>=0 else d-0.1, i, f'+{d:.2f}%' if d>=0 else f'{d:.2f}%',
             va='center', ha='left' if d>=0 else 'right', fontsize=9, fontweight='bold')

plt.tight_layout()
plt.savefig('chart_dq_before_after.png', dpi=150, bbox_inches='tight')
plt.show()
print('💾 Chart disimpan: chart_dq_before_after.png')
print('\n🏁 LAB 2 SELESAI! Dataset bersih siap untuk LAB 3: Duplicate Detection & Matching')
