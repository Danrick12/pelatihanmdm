# ============================================================
# CELL 1: LIBRARY TAMBAHAN LAB 2
# ============================================================

# Note: Pastikan library berikut sudah terinstall di environment Anda:
# pip install fuzzywuzzy python-Levenshtein unidecode jellyfish

print('✅ Library tambahan siap digunakan')

# ============================================================
# CELL 2: IMPORT LIBRARY
# ============================================================

import pandas as pd
import numpy as np
import re
import warnings
import json
from datetime import datetime
warnings.filterwarnings('ignore')

# String processing
from unidecode   import unidecode      # normalisasi unicode → ASCII
from fuzzywuzzy  import fuzz           # fuzzy string matching
import jellyfish                        # Jaro-Winkler, Soundex

# Visualisasi
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

# Setting display
pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', 60)
pd.set_option('display.float_format', '{:.2f}'.format)
pd.set_option('display.width', 130)
sns.set_theme(style='whitegrid')
plt.rcParams['figure.figsize'] = (13, 5)

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

print('✅ Semua library berhasil diimport!')

# ============================================================
# CELL 3: LOAD DATASET DARI LAB 1
# ============================================================

try:
    df_raw = pd.read_csv(
        'data/raw/ceisa_data.csv',
        dtype={
            'npwp': str,
            'nik': str,
            'telepon': str,
            'kode_pos': str
        }
    )
    print(f'✅ Dataset berhasil dimuat dari file CSV')
except FileNotFoundError:
    print('❌ File tidak ditemukan di data/raw/ceisa_data.csv')
    raise

# Buat salinan kerja — JANGAN modifikasi df_raw langsung!
# df_raw adalah data asli yang menjadi referensi/backup
df_clean = df_raw.copy()

# Konversi tipe data dasar
df_clean['tanggal_daftar'] = pd.to_datetime(df_clean['tanggal_daftar'], errors='coerce')
df_clean['penghasilan']    = pd.to_numeric(df_clean['penghasilan'],    errors='coerce')

print(f'   Shape dataset    : {df_clean.shape}')
print(f'   Kolom            : {list(df_clean.columns)}')
print(f'   Memory usage     : {df_clean.memory_usage(deep=True).sum()/1024:.1f} KB')
print(f'')
print(f'   Dataset asli (df_raw)  → JANGAN dimodifikasi, sebagai backup')
print(f'   Dataset kerja (df_clean) → tempat semua proses cleansing berlangsung')
# ============================================================
# CELL 4: SISTEM AUDIT TRAIL
# Mencatat setiap operasi cleansing yang dilakukan
# ============================================================

class AuditTrail:
    """
    Sistem pencatatan perubahan data (audit trail) untuk proses cleansing.
    Setiap operasi cleansing harus dicatat menggunakan instance ini.
    """
    def __init__(self, dataset_name: str, total_records: int):
        self.dataset_name  = dataset_name
        self.total_records = total_records
        self.start_time    = datetime.now()
        self.entries       = []   # daftar semua perubahan
        self.step_counter  = 0

    def log(self, operation: str, field: str, n_affected: int,
            description: str, before_sample: str = '', after_sample: str = ''):
        """Catat satu operasi cleansing ke dalam audit log."""
        self.step_counter += 1
        entry = {
            'step'          : self.step_counter,
            'timestamp'     : datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'operation'     : operation,
            'field'         : field,
            'n_affected'    : n_affected,
            'pct_affected'  : round(n_affected / self.total_records * 100, 2),
            'description'   : description,
            'before_sample' : before_sample,
            'after_sample'  : after_sample,
        }
        self.entries.append(entry)
        # Cetak ringkasan langsung
        pct = entry['pct_affected']
        icon = '🟢' if pct < 5 else '🟡' if pct < 15 else '🔴'
        print(f'  [{self.step_counter:02d}] {icon} {operation:<22} | {field:<20} | {n_affected:>6} record ({pct:>5.1f}%)')
        if before_sample and after_sample:
            print(f'       Sebelum: {before_sample}')
            print(f'       Sesudah: {after_sample}')

    def summary(self):
        """Tampilkan ringkasan semua operasi cleansing."""
        duration = (datetime.now() - self.start_time).seconds
        print('\n' + '='*70)
        print(f'  AUDIT TRAIL SUMMARY — {self.dataset_name}')
        print(f'  Durasi proses : {duration} detik')
        print(f'  Total operasi : {self.step_counter}')
        print('='*70)
        print(f'  {"Step":<5} {"Operasi":<22} {"Field":<20} {"Affected":>8}  {"Persen":>6}')
        print('-'*70)
        for e in self.entries:
            print(f'  {e["step"]:>4}  {e["operation"]:<22} {e["field"]:<20} {e["n_affected"]:>8,}  {e["pct_affected"]:>5.1f}%')
        print('='*70)

    def to_dataframe(self):
        """Export audit trail ke DataFrame untuk disimpan sebagai CSV."""
        return pd.DataFrame(self.entries)


# Inisialisasi audit trail untuk sesi LAB 2
audit = AuditTrail('Master Data Wajib Pajak', total_records=len(df_clean))

print(f'✅ Sistem Audit Trail siap!')
print(f'   Dataset: {audit.dataset_name}')
print(f'   Total record: {audit.total_records:,}')
print(f'   Waktu mulai: {audit.start_time.strftime("%Y-%m-%d %H:%M:%S")}')
print(f'')
print(f'Format log: [Step] Icon Operasi | Field | Jumlah Record (Persen)')
# ============================================================
# CELL 5: STANDARDISASI NAMA WAJIB PAJAK
# Menangani: casing, whitespace, karakter khusus, unicode
# ============================================================

import re
import pandas as pd
from unidecode import unidecode

def standardize_nama(nama: str) -> str:
    """
    Standardisasi nama Wajib Pajak:
    - Menghapus titik salah tempat pada semua badan usaha (PT, CV, Koperasi, dll.)
    - Menangani kombinasi badan usaha ganda (CV. UD -> CV UD, PT. PD -> PT PD)
    - Menghapus duplikasi badan usaha (PT PT -> PT)
    - Melindungi gelar akademik seperti S.Pt. agar tidak rusak
    """
    if pd.isna(nama) or str(nama).strip() == '':
        return None

    s = str(nama)

    # 1. Strip & Normalisasi spasi awal
    s = s.strip()
    s = re.sub(r'\s+', ' ', s)

    # 2. Hapus karakter tidak diinginkan (kecuali . , - ')
    s = re.sub(r"[^a-zA-Z0-9\s.,\-']", '', s)

    # 3. Transliterasi unicode → ASCII
    s = unidecode(s)

    # 4. Title Case awal
    s = s.title()

    # 5. HAPUS TITIK setelah kata operasional utuh
    bad_dots_fixes = {
        r'\bKoperasi\.': 'Koperasi',
        r'\bFirma\.':    'Firma',
        r'\bPerum\.':    'Perum',
    }
    for pattern, replacement in bad_dots_fixes.items():
        s = re.sub(pattern, replacement, s, flags=re.IGNORECASE)

    # 6. PERBAIKI KAPITALISASI SINGKATAN (Proteksi S.Pt)
    s = re.sub(r'(?<!S\.)\bPt\b', 'PT', s, flags=re.IGNORECASE)

    abbrev_fixes = {
        r'\bCv\b': 'CV',
        r'\bUd\b': 'UD',
        r'\bPd\b': 'PD',
        r'\bTbk\b': 'Tbk',
        r'\bM\.Ti\b': 'M.Ti',
        r'\bDan\b': 'dan',
        r'\bDi\b': 'di',
        r'\bThe\b': 'the',
        r'\bOf\b': 'of',
    }
    for pattern, replacement in abbrev_fixes.items():
        s = re.sub(pattern, replacement, s, flags=re.IGNORECASE)

    # 7. HAPUS TITIK DI ANTARA BADAN USAHA / SINGKATAN
    # Menghapus titik setelah PT, CV, UD, PD jika diikuti oleh spasi dan kata lain
    # Contoh: "CV. UD" -> "CV UD", "PT. PD" -> "PT PD", "PT. Indofood" -> "PT Indofood"
    s = re.sub(r'\b(PT|CV|UD|PD)\.\s+', r'\1 ', s)

    # 8. HAPUS DUPLIKASI BADAN USAHA YANG MUNCUL GANDA
    s = re.sub(r'\b(PT|CV|UD|PD)\b(?:\s*[\.?]\s*)\b\1\b', r'\1', s, flags=re.IGNORECASE)
    s = re.sub(r'\b(PT|CV|UD|PD)\s+\1\b', r'\1', s, flags=re.IGNORECASE)

    # 9. Bersihkan sisa spasi ganda atau double titik (..) di akhir kalimat
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'\.+', '.', s)

    return s.strip()


# Terapkan ke kolom nama_wp
n_before = df_clean['nama_wp'].nunique()

# Simpan nama asli untuk audit
df_clean['nama_wp_original'] = df_clean['nama_wp'].copy()
df_clean['nama_wp']          = df_clean['nama_wp'].apply(standardize_nama)

n_changed = (df_clean['nama_wp'] != df_clean['nama_wp_original']).sum()
n_after   = df_clean['nama_wp'].nunique()

# Catat ke audit trail
audit.log(
    operation   = 'STANDARDIZE_TEXT',
    field       = 'nama_wp',
    n_affected  = n_changed,
    description = 'Title Case, hapus spasi ganda, hapus karakter khusus, unidecode',
    before_sample = str(df_clean[df_clean['nama_wp'] != df_clean['nama_wp_original']]['nama_wp_original'].iloc[0]) if n_changed > 0 else '-',
    after_sample  = str(df_clean[df_clean['nama_wp'] != df_clean['nama_wp_original']]['nama_wp'].iloc[0])          if n_changed > 0 else '-',
)

# Tampilkan sampel perubahan
print(f'\n📊 HASIL STANDARDISASI NAMA WP:')
print(f'   Record diubah     : {n_changed:,} dari {len(df_clean):,} total')
print(f'   Unique nama sebelum: {n_before:,}')
print(f'   Unique nama sesudah: {n_after:,}')
print(f'')
# Tampilkan 10 contoh perubahan
changed = df_clean[df_clean['nama_wp'] != df_clean['nama_wp_original']][
    ['nama_wp_original','nama_wp']
].head(10)
changed.columns = ['SEBELUM','SESUDAH']
print('   Contoh perubahan:')
display(changed)
# ============================================================
# CELL 6: STANDARDISASI ALAMAT
# Menstandarkan format penulisan alamat
# ============================================================

# Kamus singkatan jalan yang distandarkan
JALAN_MAP = {
    r'\bJL\.?\b'      : 'Jl.',   r'\bJLN\.?\b'     : 'Jl.',
    r'\bJALAN\b'       : 'Jl.',   r'\bGG\.?\b'       : 'Gg.',
    r'\bGANG\b'        : 'Gg.',   r'\bKEC\.?\b'      : 'Kec.',
    r'\bKECAMATAN\b'   : 'Kec.',  r'\bKAB\.?\b'      : 'Kab.',
    r'\bKABUPATEN\b'   : 'Kab.',  r'\bKEL\.?\b'      : 'Kel.',
    r'\bKELURAHAN\b'   : 'Kel.',  r'\bBLOK\b'         : 'Blok',
    r'\bNO\.?\b'      : 'No.',   r'\bNOMOR\b'        : 'No.',
    r'\bRT\.?\b'      : 'RT',    r'\bRW\.?\b'       : 'RW',
}

def standardize_alamat(alamat: str) -> str:
    """Standardisasi format penulisan alamat."""
    if pd.isna(alamat) or str(alamat).strip() == '':
        return None

    s = str(alamat).strip()

    # Title case dulu
    s = s.title()

    # Normalisasi spasi
    s = re.sub(r'\s+', ' ', s)

    # Terapkan singkatan baku (case-insensitive)
    for pattern, replacement in JALAN_MAP.items():
        s = re.sub(pattern, replacement, s, flags=re.IGNORECASE)

    return s.strip()


# Terapkan standardisasi alamat
df_clean['alamat_original'] = df_clean['alamat'].copy()
df_clean['alamat']          = df_clean['alamat'].apply(standardize_alamat)

# Standardisasi kolom kelurahan dan kota
df_clean['kelurahan'] = df_clean['kelurahan'].str.strip().str.title()
df_clean['kota']      = df_clean['kota'].str.strip().str.title()

n_changed_alamat = (df_clean['alamat'] != df_clean['alamat_original']).sum()

audit.log(
    operation   = 'STANDARDIZE_TEXT',
    field       = 'alamat',
    n_affected  = n_changed_alamat,
    description = 'Title Case, singkatan jalan baku (Jl., Gg., Kec., dll.)',
)

print(f'✅ Standardisasi alamat selesai: {n_changed_alamat:,} record diubah')
print(f'\n   Contoh hasil:')
sample_change = df_clean[df_clean['alamat'] != df_clean['alamat_original']][
    ['alamat_original','alamat']
].head(6)
sample_change.columns = ['SEBELUM','SESUDAH']
display(sample_change)
# ============================================================
# CELL 6 (REVISI FINAL): STANDARDISASI ALAMAT
# ============================================================

import re
import pandas as pd
from unidecode import unidecode

# ============================================================
# KAMUS NORMALISASI
# ============================================================

JALAN_MAP = {
    r'\bJALAN\b'       : 'Jl.',
    r'\bJLN\b'         : 'Jl.',
    r'\bJL\b'          : 'Jl.',

    r'\bGANG\b'        : 'Gg.',
    r'\bGG\b'          : 'Gg.',

    r'\bKECAMATAN\b'   : 'Kec.',
    r'\bKEC\b'         : 'Kec.',

    r'\bKABUPATEN\b'   : 'Kab.',
    r'\bKAB\b'         : 'Kab.',

    r'\bKELURAHAN\b'   : 'Kel.',
    r'\bKEL\b'         : 'Kel.',

    r'\bNOMOR\b'       : 'No.',
    r'\bNO\b'          : 'No.',

    r'\bBLOK\b'        : 'Blok',

    r'\bRT\b'          : 'RT',
    r'\bRW\b'          : 'RW',
}

# ============================================================
# FUNGSI STANDARDISASI
# ============================================================

def standardize_alamat(alamat: str) -> str:

    if pd.isna(alamat):
        return None

    s = str(alamat).strip()

    if s == '':
        return None

    # ========================================================
    # 1. UNICODE NORMALIZATION
    # ========================================================

    s = unidecode(s)

    # ========================================================
    # 2. NORMALISASI SPASI
    # ========================================================

    s = re.sub(r'\s+', ' ', s)

    # ========================================================
    # 3. REMOVE SPECIAL CHARS BERLEBIHAN
    # ========================================================

    # Tetap pertahankan:
    # titik, slash, dash, koma, kurung
    s = re.sub(r"[^a-zA-Z0-9\s.,()/#\-]", '', s)

    # ========================================================
    # 4. TITLE CASE SEMENTARA
    # ========================================================

    s = s.title()

    # ========================================================
    # 5. NORMALISASI SINGKATAN
    # ========================================================

    for pattern, replacement in JALAN_MAP.items():

        s = re.sub(
            pattern,
            replacement,
            s,
            flags=re.IGNORECASE
        )

    # ========================================================
    # 6. FIX DOUBLE DOTS
    # ========================================================

    # Jl.. -> Jl.
    # No.. -> No.
    s = re.sub(r'\.\.+', '.', s)

    # ========================================================
    # 7. FIX SPACING
    # ========================================================

    # Spasi sebelum titik
    s = re.sub(r'\s+\.', '.', s)

    # Multiple spaces
    s = re.sub(r'\s+', ' ', s)

    # ========================================================
    # 8. PRESERVE COMMON ACRONYM ROADS
    # ========================================================

    ROAD_FIXES = {
        r'\bM\.H\b'   : 'M.H',
        r'\bA\.Yani\b': 'A. Yani',
        r'\bHos\b'    : 'HOS',
        r'\bAh\b'     : 'AH',
    }

    for pattern, replacement in ROAD_FIXES.items():

        s = re.sub(pattern, replacement, s)

    return s.strip()


# ============================================================
# APPLY TRANSFORMATION
# ============================================================

print('=' * 70)
print('STANDARDISASI ALAMAT')
print('=' * 70)

# Backup original
df_clean['alamat_original'] = df_clean['alamat'].copy()

# Apply
df_clean['alamat'] = df_clean['alamat'].apply(
    standardize_alamat
)

# ============================================================
# STANDARDISASI KELURAHAN & KOTA
# ============================================================

def normalize_wilayah(x):

    if pd.isna(x):
        return None

    x = str(x).strip()

    if x == '':
        return None

    x = unidecode(x)

    x = re.sub(r'\s+', ' ', x)

    return x.title()


df_clean['kelurahan'] = df_clean['kelurahan'].apply(
    normalize_wilayah
)

df_clean['kota'] = df_clean['kota'].apply(
    normalize_wilayah
)

# ============================================================
# HITUNG PERUBAHAN REAL
# ============================================================

mask_changed = (
    df_clean['alamat'].fillna('') !=
    df_clean['alamat_original'].fillna('')
)

n_changed_alamat = mask_changed.sum()

# ============================================================
# AUDIT TRAIL
# ============================================================

if n_changed_alamat > 0:

    before_sample = str(
        df_clean.loc[
            mask_changed,
            'alamat_original'
        ].iloc[0]
    )

    after_sample = str(
        df_clean.loc[
            mask_changed,
            'alamat'
        ].iloc[0]
    )

else:

    before_sample = '-'
    after_sample  = '-'


audit.log(
    operation     = 'STANDARDIZE_TEXT',
    field         = 'alamat',
    n_affected    = int(n_changed_alamat),
    description   = (
        'Normalisasi alamat, singkatan baku '
        '(Jl., Gg., Kec., Kel., No.), '
        'cleanup spasi & karakter'
    ),
    before_sample = before_sample,
    after_sample  = after_sample,
)

# ============================================================
# OUTPUT
# ============================================================

print(f'\n✅ Standardisasi alamat selesai')
print(f'   Record berubah : {n_changed_alamat:,}')
print(f'   Persentase     : {n_changed_alamat/len(df_clean)*100:.1f}%')

print('\n📝 Contoh hasil:')

sample_change = (
    df_clean.loc[
        mask_changed,
        ['alamat_original', 'alamat']
    ]
    .head(10)
    .copy()
)

sample_change.columns = ['SEBELUM', 'SESUDAH']

display(sample_change)

# ============================================================
# QUALITY CHECK
# ============================================================

remaining_double_dot = df_clean['alamat'].str.contains(
    r'\.\.',
    regex=True,
    na=False
).sum()

print('\n🔍 QUALITY CHECK')

print(f'Double dot tersisa : {remaining_double_dot:,}')

if remaining_double_dot > 0:
    print('⚠️ Masih ada alamat bermasalah')
else:
    print('✅ Tidak ditemukan double dot')# ============================================================
# CELL 7: STANDARDISASI FORMAT NPWP
# Format baku DJP: XX.XXX.XXX.X-XXX.XXX
# ============================================================

NPWP_PATTERN_VALID = r'^\d{2}\.\d{3}\.\d{3}\.\d{1}-\d{3}\.\d{3}$'

def clean_npwp(npwp) -> dict:
    """
    Bersihkan dan standardisasi format NPWP.
    Returns dict: {'value': str, 'status': 'VALID'|'INVALID'|'FIXED', 'note': str}
    """
    if pd.isna(npwp):
        return {'value': None, 'status': 'MISSING', 'note': 'NPWP kosong'}

    raw = str(npwp).strip()

    # Sudah dalam format valid — tidak perlu diubah
    if re.match(NPWP_PATTERN_VALID, raw):
        return {'value': raw, 'status': 'VALID', 'note': 'Format sudah benar'}

    # Coba perbaiki: ambil semua digit, lalu reformat
    digits = re.sub(r'\D', '', raw)  # hapus semua non-digit

    if len(digits) == 15:
        # Reformat ke XX.XXX.XXX.X-XXX.XXX
        fixed = (f'{digits[0:2]}.{digits[2:5]}.{digits[5:8]}.'
                 f'{digits[8]}-{digits[9:12]}.{digits[12:15]}')
        return {'value': fixed, 'status': 'FIXED',
                'note': f'Direformat dari: {raw}'}

    # Tidak bisa diperbaiki — digit tidak tepat 15
    return {'value': raw, 'status': 'INVALID',
            'note': f'Digit={len(digits)}, tidak bisa direformat'}


# Terapkan ke seluruh dataset
df_clean['npwp_original'] = df_clean['npwp'].copy()

npwp_results              = df_clean['npwp'].apply(clean_npwp)
df_clean['npwp']          = npwp_results.apply(lambda x: x['value'])
df_clean['npwp_status']   = npwp_results.apply(lambda x: x['status'])
df_clean['npwp_note']     = npwp_results.apply(lambda x: x['note'])

# Ringkasan hasil
status_counts = df_clean['npwp_status'].value_counts()
n_fixed       = (df_clean['npwp_status'] == 'FIXED').sum()
n_invalid     = (df_clean['npwp_status'] == 'INVALID').sum()

audit.log(
    operation   = 'FORMAT_NPWP',
    field       = 'npwp',
    n_affected  = n_fixed,
    description = f'Reformat NPWP ke XX.XXX.XXX.X-XXX.XXX | Fixed:{n_fixed} | Invalid:{n_invalid}',
)

print('📊 HASIL STANDARDISASI NPWP:')
print(f'   Status Distribusi:')
for status, count in status_counts.items():
    pct = count/len(df_clean)*100
    bar = '█' * int(pct/2)
    print(f'   {status:<10} : {count:>6,} ({pct:5.1f}%) {bar}')

print(f'\n   Contoh NPWP yang berhasil diperbaiki (FIXED):')
fixed_sample = df_clean[df_clean['npwp_status']=='FIXED'][
    ['npwp_original','npwp','npwp_note']
].head(5)
display(fixed_sample)

print(f'\n   Contoh NPWP yang tidak bisa diperbaiki (INVALID):')
invalid_sample = df_clean[df_clean['npwp_status']=='INVALID'][
    ['id_record','npwp_original','npwp_note']
].head(5)
display(invalid_sample)
# ============================================================
# CELL 8: STANDARDISASI NIK
# NIK hanya untuk WP Orang Pribadi, format: 16 digit numerik
# ============================================================

def clean_nik(row) -> dict:
    """
    Validasi dan bersihkan NIK.
    Badan tidak punya NIK → set None.
    Orang Pribadi wajib punya NIK 16 digit.
    """
    jenis = row['jenis_wp']
    nik   = row['nik']

    # WP Badan tidak memiliki NIK
    if jenis == 'Badan':
        return {'value': None, 'status': 'N/A', 'note': 'WP Badan tidak memiliki NIK'}

    # WP Orang Pribadi
    if pd.isna(nik) or str(nik).strip() == '' or str(nik) == 'None':
        return {'value': None, 'status': 'MISSING', 'note': 'NIK tidak tersedia'}

    digits = re.sub(r'\D', '', str(nik))  # ambil digit saja

    if len(digits) == 16:
        return {'value': digits, 'status': 'VALID', 'note': 'NIK valid 16 digit'}
    else:
        return {'value': None, 'status': 'INVALID',
                'note': f'NIK memiliki {len(digits)} digit (harus 16)'}


# Terapkan per baris (perlu data jenis_wp dan nik sekaligus)
df_clean['nik_original'] = df_clean['nik'].copy()

nik_results            = df_clean[['jenis_wp','nik']].apply(clean_nik, axis=1)
df_clean['nik']        = nik_results.apply(lambda x: x['value'])
df_clean['nik_status'] = nik_results.apply(lambda x: x['status'])

# Ringkasan
nik_summary = df_clean['nik_status'].value_counts()
n_nik_invalid = (df_clean['nik_status'] == 'INVALID').sum()

audit.log(
    operation   = 'VALIDATE_NIK',
    field       = 'nik',
    n_affected  = n_nik_invalid,
    description = 'Validasi 16 digit, set None untuk Badan dan NIK invalid',
)

print('📊 HASIL STANDARDISASI NIK:')
for status, count in nik_summary.items():
    pct = count/len(df_clean)*100
    print(f'   {status:<10} : {count:>6,} ({pct:5.1f}%)')
# ============================================================
# CELL 9: STANDARDISASI NOMOR TELEPON & EMAIL
# ============================================================

# ── TELEPON ──
def clean_telepon(phone) -> dict:
    """
    Standardisasi nomor telepon ke format: 08XXXXXXXXXX
    Menangani format: +62xxx, 62xxx, 08xxx, (08x) xxx-xxxx
    """
    if pd.isna(phone) or str(phone).strip() == '':
        return {'value': None, 'status': 'MISSING'}

    raw    = str(phone).strip()
    digits = re.sub(r'\D', '', raw)  # ambil digit saja

    # Konversi awalan internasional → format lokal
    if digits.startswith('62'):
        digits = '0' + digits[2:]
    elif digits.startswith('0062'):
        digits = '0' + digits[4:]

    # Validasi: harus diawali 08 dan panjang 10-13 digit
    if re.match(r'^08\d{8,11}$', digits):
        return {'value': digits, 'status': 'VALID'}
    else:
        return {'value': None, 'status': 'INVALID'}


# ── EMAIL ──
def clean_email(email) -> dict:
    """Validasi dan normalisasi email (lowercase)."""
    if pd.isna(email) or str(email).strip() == '':
        return {'value': None, 'status': 'MISSING'}

    raw = str(email).strip().lower()  # email selalu lowercase

    # Pattern email dasar (RFC 5322 simplified)
    if re.match(r'^[\w.+\-]+@[\w\-]+\.[a-z]{2,}$', raw):
        return {'value': raw, 'status': 'VALID'}
    else:
        return {'value': None, 'status': 'INVALID'}


# Terapkan ke dataset
df_clean['telepon_original'] = df_clean['telepon'].copy()
df_clean['email_original']   = df_clean['email'].copy()

tel_results = df_clean['telepon'].apply(clean_telepon)
df_clean['telepon']        = tel_results.apply(lambda x: x['value'])
df_clean['telepon_status'] = tel_results.apply(lambda x: x['status'])

em_results = df_clean['email'].apply(clean_email)
df_clean['email']        = em_results.apply(lambda x: x['value'])
df_clean['email_status'] = em_results.apply(lambda x: x['status'])

# Ringkasan
n_tel_fixed = (df_clean['telepon_status'] == 'VALID').sum()
n_em_fixed  = (df_clean['email_status']   == 'VALID').sum()

audit.log('FORMAT_PHONE','telepon',
    (df_clean['telepon_status']=='INVALID').sum(),
    'Standardisasi ke 08XXXXXXXXXX, set None jika invalid')
audit.log('FORMAT_EMAIL','email',
    (df_clean['email_status']=='INVALID').sum(),
    'Lowercase, validasi pattern email, set None jika invalid')

print('📊 TELEPON:')
for s, c in df_clean['telepon_status'].value_counts().items():
    print(f'   {s:<10}: {c:>6,} ({c/len(df_clean)*100:.1f}%)')
print('\n📊 EMAIL:')
for s, c in df_clean['email_status'].value_counts().items():
    print(f'   {s:<10}: {c:>6,} ({c/len(df_clean)*100:.1f}%)')
# ============================================================
# CELL 10: HANDLING MISSING VALUES PER STRATEGI
# ============================================================

# ── Strategi 1: KLU — impute dengan nilai default ──
n_klu_missing = df_clean['klu_kode'].isna().sum()
df_clean['klu_kode']  = df_clean['klu_kode'].fillna('99999')
df_clean['klu_nama']  = df_clean['klu_nama'].fillna('BELUM TERKLASIFIKASI')

audit.log('IMPUTE_DEFAULT','klu_kode', n_klu_missing,
          "Isi missing KLU dengan '99999 - BELUM TERKLASIFIKASI'")

# ── Strategi 2: Email — isi dengan format default ──
n_email_still_missing = df_clean['email'].isna().sum()
# Gunakan id_record sebagai bagian dari email default
df_clean['email'] = df_clean.apply(
    lambda r: f"{r['id_record'].lower().replace('wp','wp.')}@noemail.djp.go.id"
    if pd.isna(r['email']) else r['email'],
    axis=1
)
audit.log('IMPUTE_DEFAULT','email', n_email_still_missing,
          'Isi missing email dengan format id_record@noemail.djp.go.id')

# ── Strategi 3: Kode Pos — lookup dari mode kota ──
n_kodepos_missing = df_clean['kode_pos'].isna().sum()

# Buat lookup: kota → kode_pos paling umum (mode)
kodepos_lookup = (
    df_clean[df_clean['kode_pos'].notna()]
    .groupby('kota')['kode_pos']
    .agg(lambda x: x.mode()[0] if len(x.mode()) > 0 else None)
    .to_dict()
)

df_clean['kode_pos'] = df_clean.apply(
    lambda r: kodepos_lookup.get(r['kota'], '00000')
    if pd.isna(r['kode_pos']) else r['kode_pos'],
    axis=1
)

audit.log('IMPUTE_LOOKUP','kode_pos', n_kodepos_missing,
          'Isi missing kode_pos dari lookup mode kode_pos per kota')

# ── Strategi 4: NIK Invalid — flag untuk eskalasi ──
n_nik_flagged = (df_clean['nik_status'] == 'INVALID').sum()
df_clean['flag_review'] = df_clean.apply(
    lambda r: 'NIK_PERLU_VERIFIKASI' if r['nik_status'] == 'INVALID' else None,
    axis=1
)

audit.log('FLAG_REVIEW','nik', n_nik_flagged,
          'Flag record dengan NIK invalid untuk verifikasi manual Data Steward')

# ── Ringkasan ──
print('📊 RINGKASAN HANDLING MISSING VALUES:')
print(f'   KLU di-impute         : {n_klu_missing:,} record')
print(f'   Email di-impute       : {n_email_still_missing:,} record')
print(f'   Kode Pos di-impute    : {n_kodepos_missing:,} record')
print(f'   NIK di-flag review    : {n_nik_flagged:,} record')
print(f'')
# Cek sisa missing values pada field kritis
critical_fields = ['npwp','nama_wp','jenis_wp','status_wp','kode_kpp']
print('📋 Sisa missing values pada field kritis:')
for f in critical_fields:
    n_miss = df_clean[f].isna().sum()
    status = '✅' if n_miss == 0 else '⚠'
    print(f'   {status} {f:<20}: {n_miss} missing')
# ============================================================
# CELL 11: VALIDASI REFERENSIAL
# Pastikan kode dan nama referensi selalu konsisten
# ============================================================

# Tabel referensi resmi (ground truth)
PROVINSI_REF = {
    '11':'Aceh', '12':'Sumatera Utara', '13':'Sumatera Barat',
    '14':'Riau', '15':'Jambi', '16':'Sumatera Selatan',
    '17':'Bengkulu', '18':'Lampung', '19':'Kep. Bangka Belitung',
    '21':'Kep. Riau', '31':'DKI Jakarta', '32':'Jawa Barat',
    '33':'Jawa Tengah', '34':'DI Yogyakarta', '35':'Jawa Timur',
    '36':'Banten', '51':'Bali', '52':'Nusa Tenggara Barat',
    '53':'Nusa Tenggara Timur', '61':'Kalimantan Barat',
    '62':'Kalimantan Tengah', '63':'Kalimantan Selatan',
    '64':'Kalimantan Timur', '65':'Kalimantan Utara',
    '71':'Sulawesi Utara', '72':'Sulawesi Tengah',
    '73':'Sulawesi Selatan', '74':'Sulawesi Tenggara',
    '75':'Gorontalo', '76':'Sulawesi Barat',
    '81':'Maluku', '82':'Maluku Utara',
    '91':'Papua Barat', '94':'Papua',
}

KPP_REF = {
    '0610':'KPP Pratama Jakarta Pusat Satu',
    '0611':'KPP Pratama Jakarta Pusat Dua',
    '0621':'KPP Pratama Jakarta Selatan Satu',
    '0622':'KPP Pratama Jakarta Selatan Dua',
    '0631':'KPP Pratama Jakarta Timur Satu',
    '0641':'KPP Pratama Jakarta Barat Satu',
    '0711':'KPP Pratama Bandung Cibeunying',
    '0712':'KPP Pratama Bandung Cicadas',
    '0811':'KPP Pratama Semarang Tengah Satu',
    '0821':'KPP Pratama Yogyakarta',
    '0911':'KPP Pratama Surabaya Krembangan',
    '0912':'KPP Pratama Surabaya Gubeng',
    '1011':'KPP Pratama Tangerang Barat',
    '1111':'KPP Pratama Denpasar Barat',
    '1211':'KPP Pratama Makassar Utara',
}

# ── Validasi Provinsi ──
# Perbaiki nama_provinsi berdasarkan kode_provinsi (ground truth)
df_clean['nama_provinsi_original'] = df_clean['nama_provinsi'].copy()
df_clean['nama_provinsi']          = df_clean['kode_provinsi'].map(PROVINSI_REF)

n_prov_fixed = (
    df_clean['nama_provinsi'] != df_clean['nama_provinsi_original']
).sum()

audit.log('REF_VALIDATION','nama_provinsi', n_prov_fixed,
          'Sinkronisasi nama_provinsi berdasarkan kode_provinsi (ground truth)')

print(f'✅ Provinsi: {n_prov_fixed:,} nama_provinsi diperbaiki dari kode referensi')

# ── Validasi KPP ──
df_clean['nama_kpp_original'] = df_clean['nama_kpp'].copy()
df_clean['nama_kpp']          = df_clean['kode_kpp'].map(KPP_REF)

# Jika kode_kpp tidak ada di referensi, tandai sebagai tidak dikenal
df_clean['nama_kpp'] = df_clean['nama_kpp'].fillna('KPP TIDAK DIKENAL')

n_kpp_fixed = (
    df_clean['nama_kpp'] != df_clean['nama_kpp_original']
).sum()

audit.log('REF_VALIDATION','nama_kpp', n_kpp_fixed,
          'Sinkronisasi nama_kpp berdasarkan kode_kpp (ground truth)')

print(f'✅ KPP: {n_kpp_fixed:,} nama_kpp disinkronkan dari kode referensi')

# ── Validasi Status WP ──
valid_status_wp = ['Aktif', 'Non-Aktif', 'Hapus']
n_invalid_status = (~df_clean['status_wp'].isin(valid_status_wp)).sum()
df_clean.loc[~df_clean['status_wp'].isin(valid_status_wp), 'status_wp'] = 'Aktif'

audit.log('REF_VALIDATION','status_wp', n_invalid_status,
          f'Set nilai status_wp invalid ke Aktif (default). Valid: {valid_status_wp}')

print(f'✅ Status WP: {n_invalid_status:,} nilai tidak valid diperbaiki ke default Aktif')

# ── Tampilkan contoh perbaikan ──
if n_prov_fixed > 0:
    print(f'\n   Contoh perbaikan nama_provinsi:')
    sample = df_clean[
        df_clean['nama_provinsi'] != df_clean['nama_provinsi_original']
    ][['kode_provinsi','nama_provinsi_original','nama_provinsi']].head(5)
    sample.columns = ['Kode','Nama Lama','Nama Baku']
    display(sample)
# ============================================================
# CELL 11: VALIDASI REFERENSIAL
# ============================================================

print('=' * 70)
print('VALIDASI REFERENSIAL')
print('=' * 70)

# ============================================================
# REFERENCE TABLE
# ============================================================

PROVINSI_REF = {
    '11':'Aceh',
    '12':'Sumatera Utara',
    '13':'Sumatera Barat',
    '14':'Riau',
    '15':'Jambi',
    '16':'Sumatera Selatan',
    '17':'Bengkulu',
    '18':'Lampung',
    '19':'Kep. Bangka Belitung',
    '21':'Kep. Riau',
    '31':'DKI Jakarta',
    '32':'Jawa Barat',
    '33':'Jawa Tengah',
    '34':'DI Yogyakarta',
    '35':'Jawa Timur',
    '36':'Banten',
    '51':'Bali',
    '52':'Nusa Tenggara Barat',
    '53':'Nusa Tenggara Timur',
    '61':'Kalimantan Barat',
    '62':'Kalimantan Tengah',
    '63':'Kalimantan Selatan',
    '64':'Kalimantan Timur',
    '65':'Kalimantan Utara',
    '71':'Sulawesi Utara',
    '72':'Sulawesi Tengah',
    '73':'Sulawesi Selatan',
    '74':'Sulawesi Tenggara',
    '75':'Gorontalo',
    '76':'Sulawesi Barat',
    '81':'Maluku',
    '82':'Maluku Utara',
    '91':'Papua Barat',
    '94':'Papua'
}

KPP_REF = {
    '0610':'KPP Pratama Jakarta Pusat Satu',
    '0611':'KPP Pratama Jakarta Pusat Dua',
    '0621':'KPP Pratama Jakarta Selatan Satu',
    '0622':'KPP Pratama Jakarta Selatan Dua',
    '0631':'KPP Pratama Jakarta Timur Satu',
    '0641':'KPP Pratama Jakarta Barat Satu',
    '0711':'KPP Pratama Bandung Cibeunying',
    '0712':'KPP Pratama Bandung Cicadas',
    '0811':'KPP Pratama Semarang Tengah Satu',
    '0821':'KPP Pratama Yogyakarta',
    '0911':'KPP Pratama Surabaya Krembangan',
    '0912':'KPP Pratama Surabaya Gubeng',
    '1011':'KPP Pratama Tangerang Barat',
    '1111':'KPP Pratama Denpasar Barat',
    '1211':'KPP Pratama Makassar Utara'
}

# ============================================================
# NORMALISASI KODE REFERENSI
# ============================================================

# Backup original
df_clean['kode_provinsi_raw'] = df_clean['kode_provinsi']
df_clean['kode_kpp_raw'] = df_clean['kode_kpp']

# Normalisasi menjadi string bersih
df_clean['kode_provinsi_clean'] = (
    df_clean['kode_provinsi']
    .astype(str)
    .str.replace('.0', '', regex=False)
    .str.strip()
    .str.zfill(2)
)

df_clean['kode_kpp_clean'] = (
    df_clean['kode_kpp']
    .astype(str)
    .str.replace('.0', '', regex=False)
    .str.strip()
    .str.zfill(4)
)

# ============================================================
# VALIDASI PROVINSI
# ============================================================

# Backup original
df_clean['nama_provinsi_original'] = df_clean['nama_provinsi']

# Mapping referensi
df_clean['nama_provinsi_ref'] = (
    df_clean['kode_provinsi_clean']
    .map(PROVINSI_REF)
)

# Status validasi
df_clean['provinsi_status'] = np.where(
    df_clean['nama_provinsi_ref'].isna(),
    'UNKNOWN_CODE',

    np.where(
        df_clean['nama_provinsi_original']
        .fillna('')
        .str.strip()
        .str.lower()
        ==
        df_clean['nama_provinsi_ref']
        .fillna('')
        .str.lower(),

        'MATCH',
        'MISMATCH'
    )
)

# Hanya overwrite jika mismatch
mask_prov_fix = df_clean['provinsi_status'] == 'MISMATCH'

df_clean.loc[
    mask_prov_fix,
    'nama_provinsi'
] = df_clean.loc[
    mask_prov_fix,
    'nama_provinsi_ref'
]

n_prov_fixed = mask_prov_fix.sum()

audit.log(
    operation='REF_VALIDATION',
    field='nama_provinsi',
    n_affected=n_prov_fixed,
    description='Sinkronisasi nama_provinsi berdasarkan kode referensi'
)

print(f'✅ Provinsi mismatch diperbaiki: {n_prov_fixed:,}')

# ============================================================
# VALIDASI KPP
# ============================================================

df_clean['nama_kpp_original'] = df_clean['nama_kpp']

df_clean['nama_kpp_ref'] = (
    df_clean['kode_kpp_clean']
    .map(KPP_REF)
)

df_clean['kpp_status'] = np.where(
    df_clean['nama_kpp_ref'].isna(),
    'UNKNOWN_CODE',

    np.where(
        df_clean['nama_kpp_original']
        .fillna('')
        .str.strip()
        .str.lower()
        ==
        df_clean['nama_kpp_ref']
        .fillna('')
        .str.lower(),

        'MATCH',
        'MISMATCH'
    )
)

mask_kpp_fix = df_clean['kpp_status'] == 'MISMATCH'

df_clean.loc[
    mask_kpp_fix,
    'nama_kpp'
] = df_clean.loc[
    mask_kpp_fix,
    'nama_kpp_ref'
]

n_kpp_fixed = mask_kpp_fix.sum()

audit.log(
    operation='REF_VALIDATION',
    field='nama_kpp',
    n_affected=n_kpp_fixed,
    description='Sinkronisasi nama_kpp berdasarkan kode referensi'
)

print(f'✅ KPP mismatch diperbaiki: {n_kpp_fixed:,}')

# ============================================================
# VALIDASI STATUS WP
# ============================================================

valid_status_wp = [
    'Aktif',
    'Non-Aktif',
    'Hapus'
]

df_clean['status_wp_original'] = df_clean['status_wp']

mask_invalid_status = ~df_clean['status_wp'].isin(valid_status_wp)

n_invalid_status = mask_invalid_status.sum()

df_clean.loc[
    mask_invalid_status,
    'status_wp'
] = 'Aktif'

audit.log(
    operation='REF_VALIDATION',
    field='status_wp',
    n_affected=n_invalid_status,
    description='Status invalid diset ke default Aktif'
)

print(f'✅ Status WP invalid diperbaiki: {n_invalid_status:,}')

# ============================================================
# SUMMARY
# ============================================================

print('\n📊 RINGKASAN VALIDASI REFERENSIAL')
print('-' * 70)

print('\nProvinsi Status:')
print(df_clean['provinsi_status'].value_counts())

print('\nKPP Status:')
print(df_clean['kpp_status'].value_counts())

# ============================================================
# SAMPLE FIX
# ============================================================

if n_prov_fixed > 0:

    print('\n📌 Contoh perbaikan provinsi:')

    sample = df_clean.loc[
        mask_prov_fix,
        [
            'kode_provinsi_clean',
            'nama_provinsi_original',
            'nama_provinsi'
        ]
    ].head(5)

    sample.columns = [
        'Kode',
        'Nama Lama',
        'Nama Baku'
    ]

    display(sample)# ============================================================
# CELL 12: DETEKSI OUTLIER — METODE IQR
# IQR = Interquartile Range (Q3 - Q1)
# Outlier: nilai < Q1 - 1.5*IQR  atau  > Q3 + 1.5*IQR
# ============================================================

col = 'penghasilan'

# Hitung statistik IQR
Q1  = df_clean[col].quantile(0.25)
Q3  = df_clean[col].quantile(0.75)
IQR = Q3 - Q1

lower_bound = Q1 - 1.5 * IQR
upper_bound = Q3 + 1.5 * IQR

# Identifikasi outlier
mask_low  = df_clean[col] < lower_bound
mask_high = df_clean[col] > upper_bound
mask_out  = mask_low | mask_high

n_outlier_low  = mask_low.sum()
n_outlier_high = mask_high.sum()
n_outlier_total= mask_out.sum()

print('📊 DETEKSI OUTLIER — METODE IQR:')
print(f'   Q1 (25th percentile) : Rp {Q1:>20,.0f}')
print(f'   Q3 (75th percentile) : Rp {Q3:>20,.0f}')
print(f'   IQR (Q3 - Q1)        : Rp {IQR:>20,.0f}')
print(f'   Lower Bound          : Rp {lower_bound:>20,.0f}')
print(f'   Upper Bound          : Rp {upper_bound:>20,.0f}')
print(f'')
print(f'   Outlier bawah (terlalu kecil) : {n_outlier_low:>5,} record ({n_outlier_low/len(df_clean)*100:.2f}%)')
print(f'   Outlier atas  (terlalu besar) : {n_outlier_high:>5,} record ({n_outlier_high/len(df_clean)*100:.2f}%)')
print(f'   Total outlier                 : {n_outlier_total:>5,} record ({n_outlier_total/len(df_clean)*100:.2f}%)')

# ── Visualisasi distribusi penghasilan ──
fig, axes = plt.subplots(1, 3, figsize=(18, 5))
fig.suptitle('Analisis Distribusi & Outlier — Field Penghasilan', fontweight='bold')

# Chart 1: Histogram distribusi asli
ax1 = axes[0]
df_clean[col].clip(upper=df_clean[col].quantile(0.99)).plot(
    kind='hist', bins=50, ax=ax1, color='#2196F3', edgecolor='white')
ax1.set_title('Distribusi Penghasilan\n(clip 99th percentile untuk tampilan)')
ax1.set_xlabel('Penghasilan (Rp)')
ax1.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f'{x/1e6:.0f}Jt'))

# Chart 2: Boxplot
ax2 = axes[1]
df_clean[col].clip(upper=df_clean[col].quantile(0.99)).plot(
    kind='box', ax=ax2, color='#2196F3')
ax2.set_title('Boxplot Penghasilan')
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda y,_: f'{y/1e6:.0f}Jt'))

# Chart 3: Distribusi log-scale (lebih informatif untuk data skewed)
ax3 = axes[2]
np.log1p(df_clean[col]).plot(
    kind='hist', bins=50, ax=ax3, color='#4CAF50', edgecolor='white')
ax3.set_title('Distribusi Log(Penghasilan)\n(transformasi log, lebih normal)')
ax3.set_xlabel('log(Penghasilan + 1)')

plt.tight_layout()
plt.savefig('chart_outlier_penghasilan.png', dpi=150, bbox_inches='tight')
plt.show()
# ============================================================
# CELL 13: PENANGANAN OUTLIER — WINSORIZING
# Winsorizing: ganti outlier dengan batas yang masuk akal
# (lebih baik dari deletion karena mempertahankan record)
# ============================================================

# Strategi: Winsorizing pada percentile 1% dan 99%
# Artinya: nilai di bawah 1st percentile → set ke 1st percentile
#          nilai di atas 99th percentile → set ke 99th percentile
p01 = df_clean[col].quantile(0.01)  # 1st percentile
p99 = df_clean[col].quantile(0.99)  # 99th percentile

df_clean[f'{col}_original'] = df_clean[col].copy()
df_clean[col]               = df_clean[col].clip(lower=p01, upper=p99)

n_winsorized = (df_clean[col] != df_clean[f'{col}_original']).sum()

audit.log('WINSORIZE_OUTLIER', col, n_winsorized,
    f'Winsorize penghasilan ke rentang [{p01:,.0f} — {p99:,.0f}] (p1-p99)',
    before_sample=f'Min asli: Rp {df_clean[col+"_original"].min():,.0f}',
    after_sample= f'Min baru: Rp {df_clean[col].min():,.0f}',
)

print(f'✅ Winsorizing selesai:')
print(f'   Record diubah    : {n_winsorized:,}')
print(f'   Range penghasilan sebelum: Rp {df_clean[col+"_original"].min():>15,.0f} — Rp {df_clean[col+"_original"].max():>20,.0f}')
print(f'   Range penghasilan sesudah: Rp {df_clean[col].min():>15,.0f} — Rp {df_clean[col].max():>20,.0f}')

# Tambahkan kolom penghasilan_log untuk kebutuhan analitik
df_clean['penghasilan_log'] = np.log1p(df_clean['penghasilan'])
print(f'\n✅ Kolom penghasilan_log ditambahkan (nilai log1p untuk analitik)')
