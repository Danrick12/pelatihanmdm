# [LAB 0.1] DATA REFERENSI DJBC
# Berisi kode-kode referensi standar Direktorat Jenderal Bea dan Cukai (DJBC)
# sesuai dengan docs/01_data_dictionary.md

# Referensi Provinsi Indonesia (34 provinsi)
PROVINSI = {
    '11': 'Aceh',               '12': 'Sumatera Utara',
    '13': 'Sumatera Barat',      '14': 'Riau',
    '15': 'Jambi',               '16': 'Sumatera Selatan',
    '17': 'Bengkulu',            '18': 'Lampung',
    '19': 'Kep. Bangka Belitung','21': 'Kep. Riau',
    '31': 'DKI Jakarta',         '32': 'Jawa Barat',
    '33': 'Jawa Tengah',         '34': 'DI Yogyakarta',
    '35': 'Jawa Timur',          '36': 'Banten',
    '51': 'Bali',                '52': 'Nusa Tenggara Barat',
    '53': 'Nusa Tenggara Timur', '61': 'Kalimantan Barat',
    '62': 'Kalimantan Tengah',   '63': 'Kalimantan Selatan',
    '64': 'Kalimantan Timur',    '65': 'Kalimantan Utara',
    '71': 'Sulawesi Utara',      '72': 'Sulawesi Tengah',
    '73': 'Sulawesi Selatan',    '74': 'Sulawesi Tenggara',
    '75': 'Gorontalo',           '76': 'Sulawesi Barat',
    '81': 'Maluku',              '82': 'Maluku Utara',
    '91': 'Papua Barat',         '94': 'Papua',
}

# Daftar Kantor Pelayanan Bea Cukai (KPPBC)
# KODE_KANTOR yang digunakan dalam OSS & CEISA
KPPBC_LIST = [
    # Kantor Utama / Besar (sudah ada di list asli)
    {'kode': '010100', 'nama': 'KPU Bea dan Cukai Tipe A Tanjung Priok', 'wilayah': '31'},
    {'kode': '040300', 'nama': 'KPPBC TMP B Soekarno-Hatta',           'wilayah': '31'},
    {'kode': '020300', 'nama': 'KPPBC TMP Belawan',                   'wilayah': '12'},
    {'kode': '070100', 'nama': 'KPPBC TMP Tanjung Perak',             'wilayah': '35'},
    {'kode': '050100', 'nama': 'KPPBC TMP Tanjung Emas',              'wilayah': '33'},
    {'kode': '140100', 'nama': 'KPPBC TMP B Makassar',                'wilayah': '73'},
    {'kode': '060100', 'nama': 'KPPBC TMP A Pasuruan',                'wilayah': '35'},
    {'kode': '090100', 'nama': 'KPPBC TMP B Ngurah Rai',              'wilayah': '51'},

    # Tambahan utama & representatif dari berbagai wilayah
    {'kode': '010700', 'nama': 'KPPBC Tipe Madya Pabean Belawan',     'wilayah': '12'},
    {'kode': '010800', 'nama': 'KPPBC Tipe Madya Pabean B Medan',     'wilayah': '12'},
    {'kode': '011200', 'nama': 'KPPBC Tipe Madya Pabean C Kuala Tanjung', 'wilayah': '12'},
    {'kode': '020400', 'nama': 'KPU Bea dan Cukai Tipe B Batam',      'wilayah': '21'},
    {'kode': '020100', 'nama': 'KPPBC Tipe Madya Pabean B Tanjung Balai Karimun', 'wilayah': '21'},
    {'kode': '030100', 'nama': 'KPPBC Tipe Madya Pabean B Palembang', 'wilayah': '16'},
    {'kode': '030700', 'nama': 'KPPBC Tipe Madya Pabean B Bandar Lampung', 'wilayah': '18'},
    {'kode': '050400', 'nama': 'KPPBC Tipe Madya Pabean Merak',       'wilayah': '36'},
    {'kode': '050900', 'nama': 'KPPBC Tipe Madya Pabean A Bekasi',    'wilayah': '32'},
    {'kode': '070500', 'nama': 'KPPBC TMP Juanda',                    'wilayah': '35'},
    {'kode': '080100', 'nama': 'KPPBC TMP Ngurah Rai',                'wilayah': '51'},
    {'kode': '100300', 'nama': 'KPPBC Balikpapan',                    'wilayah': '64'},
    {'kode': '110100', 'nama': 'KPPBC Makassar',                      'wilayah': '73'},
    {'kode': '120300', 'nama': 'KPPBC Sorong',                        'wilayah': '91'},
    {'kode': '040400', 'nama': 'KPPBC Tipe Madya Pabean A Jakarta',   'wilayah': '31'},
    {'kode': '060300', 'nama': 'KPPBC Tipe Madya Cukai Kudus',        'wilayah': '33'},
    {'kode': '071300', 'nama': 'KPPBC Pasuruan',                      'wilayah': '35'},
    {'kode': '090400', 'nama': 'KPPBC Pontianak',                     'wilayah': '61'},
]

# --- POOLS UNTUK SIMULASI (ENUMS) ---

# Status NIB (Sesuai docs/01_data_dictionary.md §1.16)
STATUS_NIB_POOL = ['AKTIF', 'DIBEKUKAN', 'DICABUT']

# Status Badan Hukum (Sesuai docs/01_data_dictionary.md §1.6)
STATUS_BADAN_HUKUM_POOL = ['Berbadan Hukum', 'Belum Berbadan Hukum']

# Status Perseroan (Sesuai docs/01_data_dictionary.md §1.7)
STATUS_PERSEROAN_POOL = ['Aktif', 'Tidak Aktif', 'Dibekukan']

# Jenis API (Angka Pengenal Importir) (Sesuai docs/01_data_dictionary.md §1.14)
JENIS_API_POOL = ['API-U', 'API-P']

# Kategori Pelaku Usaha di CEISA (Sesuai docs/01_data_dictionary.md §2.10)
KATEGORI_CEISA_POOL = ['IMPORTIR', 'EKSPORTIR', 'KEDUA-DUANYA']

# Jenis Badan Usaha (Sesuai docs/01_data_dictionary.md §1.5)
JENIS_PERSEROAN_POOL = ['PT', 'CV', 'Firma', 'Perum', 'UD']

# Flag Fasilitas (Y/N)
FLAG_POOL = ['Y', 'N']

print(f'✅ Lab 0.1: Referensi DJBC Siap (Align dengan Data Dictionary)')
print(f'   - {len(KPPBC_LIST)} Kantor KPPBC terdaftar.')
print(f'   - {len(STATUS_NIB_POOL)} Status NIB didefinisikan.')
