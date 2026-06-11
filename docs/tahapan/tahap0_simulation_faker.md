# Tahap 0 — Data Simulation & Faker Engine

**Status**: ⬜ Direkomendasikan untuk Eksekusi

## 1. Tujuan
Membangkitkan dataset simulasi yang mencerminkan kompleksitas dunia nyata di DJBC (Bea Cukai), mencakup data legalitas dari OSS dan data operasional dari CEISA, lengkap dengan anomali yang sengaja disuntikkan untuk menguji sistem MDM.

## 2. Parameter Simulasi
- **Total Entitas Unik**: 5.000 Perusahaan.
- **Total Record Akhir**: ~6.000 - 6.500 record (setelah injeksi duplikasi).
- **Distribusi Sumber**:
  - **OSS (Master)**: ~80% dari total master.
  - **CEISA (Operational)**: ~80% dari total master.
  - **Overlap**: Area di mana matching akan dilakukan.

## 3. Spesifikasi Skema (Mengacu pada Data Dictionary)
Dataset harus menyertakan seluruh kolom yang didefinisikan di [`01_data_dictionary.md`](../01_data_dictionary.md):
- **OSS (16 kolom)**: `NIB`, `NPWP_PERSEROAN`, `NAMA_PERSEROAN`, `NAMA_SINGKATAN`, `JENIS_PERSEROAN`, `STATUS_BADAN_HUKUM`, `STATUS_PERSEROAN`, `ALAMAT_PERSEROAN`, `KELURAHAN_PERSEROAN`, `PERSEROAN_DAERAH_ID`, `KODE_POS_PERSEROAN`, `FLAG_IMPOR`, `FLAG_EKSPOR`, `JENIS_API`, `TGL_PERUBAHAN_NIB`, `STATUS_NIB`.
- **CEISA (16 kolom)**: `ID_PERUSAHAAN`, `NIB`, `NPWP` (kotor — tanpa separator), `NAMA_PERUSAHAAN` (kotor), `ALAMAT_PERUSAHAAN`, `KELURAHAN`, `DAERAH_ID`, `KODE_POS`, `NOMOR_TELPON`, `KATEGORI`, `NIPER`, `NOMOR_API`, `TGL_TERBIT_NIB`, `STATUS_NIB`, `KODE_KANTOR`, `TGL_SYNC_OSS`.

## 4. Injeksi Anomali (MDM Challenges)
Untuk membuktikan efektivitas notebook, Faker Engine harus menyuntikkan:

| Jenis Anomali | Deskripsi | Target Uji |
|---|---|---|
| **Format NPWP** | NPWP di CEISA tanpa titik/strip, di OSS rapi. | Cleansing Stage |
| **Typo Nama** | Menambahkan "(TYPO)", menghapus "PT", atau beda spasi di CEISA. | Fuzzy Matching Stage |
| **NIB Typo** | Satu digit NIB diubah di salah satu sistem. | Secondary Matching (NPWP) |
| **Konflik Status** | Status OSS 'DIBEKUKAN' vs CEISA 'AKTIF' dengan beda tanggal. | Survivorship (Latest Date) |
| **Logical Conflict** | Flag Ekspor 'N' tapi NIPER terisi di CEISA. | Business Rule Validation |
| **Orphan Records** | Record yang hanya ada di OSS atau hanya di CEISA. | Golden Record (Source Tracking) |
| **Stale Data** | `TGL_PERUBAHAN_NIB` (OSS) sangat lama (mis. > 1 tahun, contoh 2015). | Timeliness — `IS_STALE` |
| **Missing Optional Field** | Field opsional (`KELURAHAN`, `KODE_POS`, `NOMOR_TELPON`, dll) kosong; field wajib selalu terisi. | Completeness Profiling |
| **Duplicate Entry** | Satu perusahaan muncul 2x di sistem yang sama. | Duplicate Detection |
| **Data Mart Snapshot Duplicate** | `NIB` sama muncul di >1 baris CEISA dengan `NAMA_PERUSAHAAN`/`ALAMAT_PERUSAHAAN`/`TGL_SYNC_OSS` berbeda (snapshot historis). | Pre-matching Dedup (ambil snapshot terbaru) |

## 5. Referensi Implementasi
Mengacu pada pola di `archive/Source/MDM_DJBC_Professional_Full.ipynb` dan `reference/Data Profiling (1).ipynb`:
- Gunakan `Faker('id_ID')` dan `random.seed(42)` agar hasil *reproducible*.
- Implementasikan class atau fungsi `generate_djbc_record()` yang komprehensif.
- Output disimpan dalam format CSV di folder `data/raw/`:
  - `oss_nib_data.csv`
  - `ceisa_data.csv`

## 6. Checklist Eksekusi
- [ ] Inisialisasi Faker dengan Locale Indonesia.
- [ ] Generate 5.000 data master dasar.
- [ ] Lakukan *cloning* untuk 1.000 data duplikat dengan variasi anomali.
- [ ] Split menjadi dataset OSS dan CEISA.
- [ ] Ekspor ke folder `data/raw/`.

---
*Dokumen ini adalah bagian dari perencanaan Mini Project MDM Kelompok 5.*
