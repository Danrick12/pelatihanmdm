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

## 3. Spesifikasi Skema (Mengacu pada Rekomendasi)
Dataset harus menyertakan kolom yang disepakati di `docs/rekomendasi/kesimpulan_diskusi_skema.md`:
- **OSS**: NIB (13 digit), NPWP (15 digit), Nama, Alamat, Jenis Perseroan, Status NIB, Status Perseroan, TGL_TERBIT, TGL_PERUBAHAN, Flag Impor/Ekspor, Flag UMK.
- **CEISA**: NIB, NPWP (kotor), Nama (kotor), Kategori, NIPER, Nomor API, Status NIB, TGL_PERUBAHAN.

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
