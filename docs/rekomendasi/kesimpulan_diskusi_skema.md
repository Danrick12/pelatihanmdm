# Kesimpulan Diskusi Skema & Strategi MDM (DJBC)

Dokumen ini merangkum hasil diskusi antara User dan Gemini CLI mengenai arah pengembangan Mini Project MDM Kelompok 5. Dokumen ini ditujukan sebagai referensi konteks untuk asisten AI (Gemini/Claude) agar tetap selaras (*on-point*).

## 1. Filosofi Arsitektur
- **OSS (Online Single Submission) sebagai Master/System of Record:** Menjadi sumber kebenaran tunggal untuk data legalitas dan identitas perusahaan.
- **CEISA sebagai Operational System:** Sumber data untuk aktivitas transaksional kepabeanan dan fasilitas terkini.
- **Tujuan Akhir:** Membentuk *Golden Record* yang menggabungkan keabsahan legal dari OSS dan keaktifan operasional dari CEISA.

## 2. Pemilihan Kolom (Final Scope)
Berdasarkan daftar 130+ kolom "Real Data", kita membatasi cakupan agar project tetap efisien namun mencakup semua logika MDM yang diperlukan.

### A. Skema OSS (Master Identitas)
Fokus pada legalitas dan profil umum:
- **Identitas:** `NIB`, `NPWP_PERSEROAN`, `NAMA_PERSEROAN`, `NAMA_SINGKATAN`, `JENIS_PERSEROAN`.
- **Lokasi:** `ALAMAT_PERSEROAN`, `KELURAHAN_PERSEROAN`, `PERSEROAN_DAERAH_ID`, `KODE_POS_PERSEROAN`, `KODE_KANTOR`.
- **Status:** `STATUS_NIB`, `STATUS_PERSEROAN`, `STATUS_BADAN_HUKUM`.
- **Fasilitas (OSS side):** `FLAG_IMPOR`, `FLAG_EKSPOR`, `JENIS_API`, `FLAG_MITA`, `FLAG_AEO`, `FLAG_UMK`.
- **Temporal (Audit):** `TGL_TERBIT_NIB`, `TGL_PERUBAHAN_NIB`.

### B. Skema CEISA (Operational Data)
Fokus pada data transaksi dan sinkronisasi:
- **Identitas (untuk matching):** `NIB`, `NPWP`, `NAMA_PERUSAHAAN`.
- **Operasional DJBC:** `KATEGORI` (Imp/Eks), `NIPER`, `NOMOR_API`, `TANGGAL_API`, `KODE_KANTOR`.
- **Status (untuk konflik):** `STATUS_NIB`, `TGL_PERUBAHAN_NIB`.

## 3. Strategi Matching (Multi-Level)
1. **Prioritas 1 (Exact NIB):** Join utama pada 13 digit NIB yang sudah dinormalisasi.
2. **Prioritas 2 (Exact NPWP):** Jika NIB tidak match, gunakan NPWP (untuk mendeteksi typo NIB).
3. **Prioritas 3 (Fuzzy Matching):** Menggunakan nama perusahaan dan alamat jika identitas angka tidak ditemukan.

## 4. Aturan Survivorship (Golden Record)
- **Identitas Perusahaan:** WAJIB menang dari **OSS**.
- **Data Fasilitas/Kegiatan/Kantor Pelayanan:** WAJIB menang dari **CEISA** (karena bersifat transaksional/operasional terkini).
- **Status NIB:** Menggunakan logika **"Latest Date Wins"**. Membandingkan `TGL_PERUBAHAN_NIB` dari kedua sistem untuk menentukan status terkini.

## 5. Area Cleansing Utama
- **Normalisasi Nama:** Menyamakan format PT, CV, dan pembersihan karakter spesial.
- **Standardisasi NPWP:** Memastikan format `XX.XXX.XXX.X-XXX.XXX`.
- **Validasi NIB:** Memastikan string 13 digit numerik.
- **Alamat:** Standardisasi singkatan jalan (Jl.) dan Case (Title Case).

## 6. Noise (Diabaikan)
- Data administratif user aplikasi (`EMAIL_USER`, `HP_USER`, dll).
- Koordinat teknis (`LATITUDE`, `LONGITUDE`).
- Detail finansial mendalam yang tidak terkait langsung dengan profil kepabeanan.

---
**Status:** *Approved by User & Gemini CLI* (11 Juni 2026)
