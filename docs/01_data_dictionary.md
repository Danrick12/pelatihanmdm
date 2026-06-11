# Data Dictionary — OSS vs CEISA

Skema berikut diadaptasi dari simulasi sebelumnya (`archive/df_oss_nib.csv`, `archive/df_ceisa.csv`) dan akan jadi dasar regenerasi data di Step 3. Nilai contoh di bawah bersifat ilustratif — daftar nilai valid (enum) akan difinalisasi saat penulisan ulang script simulasi, mengacu ke [`02_business_rules.md`](02_business_rules.md).

## 1. Skema OSS (Online Single Submission — data legalitas/registrasi NIB)

19 kolom. OSS adalah sumber **legalitas resmi** perusahaan (apa yang terdaftar saat pengurusan izin usaha).

| # | Kolom | Tipe | Deskripsi | Contoh | Wajib? |
|---|---|---|---|---|---|
| 1 | `NIB` | string (13 digit) | Nomor Induk Berusaha — identitas utama perusahaan, **matching key** | `1043321819600` | Wajib |
| 2 | `NPWP_PERSEROAN` | string | NPWP perusahaan, format `XX.XXX.XXX.X-XXX.XXX` | `13.389.083.8-637.940` | Wajib |
| 3 | `NAMA_PERSEROAN` | string | Nama resmi badan usaha | `PT Saefullah` | Wajib |
| 4 | `NAMA_SINGKATAN` | string | Nama singkat/alias perusahaan | `PT Saefull` | Opsional |
| 5 | `JENIS_PERSEROAN` | string (enum) | Bentuk badan usaha: `PT`, `CV`, `Firma`, `Perum`, `UD` | `PT` | Wajib |
| 6 | `STATUS_BADAN_HUKUM` | string (enum) | Status legalitas badan hukum: `Berbadan Hukum`, `Belum Berbadan Hukum` | `Berbadan Hukum` | Wajib |
| 7 | `STATUS_PERSEROAN` | string (enum) | Status operasional perusahaan: `Aktif`, `Tidak Aktif`, `Dibekukan` | `Aktif` | Wajib |
| 8 | `ALAMAT_PERSEROAN` | string | Alamat lengkap perusahaan | `Jl. Dr. Djunjunan No. 8` | Wajib |
| 9 | `KELURAHAN_PERSEROAN` | string | Kelurahan/kota domisili | `Balikpapan` | Opsional |
| 10 | `PERSEROAN_DAERAH_ID` | string | Kode wilayah (referensi ke tabel kode wilayah) | `3715` | Wajib |
| 11 | `KODE_POS_PERSEROAN` | string (5 digit) | Kode pos | `96001` | Opsional |
| 12 | `FLAG_IMPOR` | string (Y/N) | Apakah punya izin importir | `Y` | Wajib |
| 13 | `FLAG_EKSPOR` | string (Y/N) | Apakah punya izin eksportir | `Y` | Wajib |
| 14 | `JENIS_API` | string (enum) | Jenis Angka Pengenal Importir: `API-U`, `API-P`, kosong jika `FLAG_IMPOR=N` | `API-U` | Kondisional |
| 15 | `TGL_PERUBAHAN_NIB` | date | Tanggal perubahan/update NIB terakhir di OSS | `2025-10-04` | Wajib |
| 16 | `STATUS_NIB` | string (enum) | Status NIB versi OSS: `AKTIF`, `DIBEKUKAN`, `DICABUT` | `AKTIF` | Wajib |
| 17 | `FLAG_MITA` | string (Y/N) | Status fasilitas Mitra Utama Kepabeanan | `Y` | Opsional |
| 18 | `FLAG_AEO` | string (Y/N) | Status Authorized Economic Operator | `N` | Opsional |
| 19 | `KODE_KANTOR` | string | Kode Kantor Bea Cukai tempat terdaftar | `010100` | Wajib |

## 2. Skema CEISA (Customs-Excise Information System and Automation — data kepabeanan)

15 kolom. CEISA adalah sumber **operasional kepabeanan** (apa yang dipakai saat transaksi impor/ekspor).

| # | Kolom | Tipe | Deskripsi | Contoh | Wajib? |
|---|---|---|---|---|---|
| 1 | `ID_PERUSAHAAN` | string | ID internal perusahaan di CEISA | `C000000` | Wajib |
| 2 | `NIB` | string (13 digit) | Nomor Induk Berusaha — **matching key** ke OSS | `1043321819600` | Wajib |
| 3 | `NPWP` | string | NPWP perusahaan, format bisa berbeda dari OSS (mis. tanpa separator) | `13.389.083.8-637.940` | Wajib |
| 4 | `NAMA_PERUSAHAAN` | string | Nama perusahaan versi CEISA (bisa beda penulisan dari OSS) | `PT Saefullah` | Wajib |
| 5 | `ALAMAT_PERUSAHAAN` | string | Alamat versi CEISA (bisa beda dari OSS) | `Jl. Dr. Djunjunan No. 8` | Wajib |
| 6 | `KELURAHAN` | string | Kelurahan/kota versi CEISA | `Malang` | Opsional |
| 7 | `DAERAH_ID` | string | Kode wilayah versi CEISA | `3715` | Wajib |
| 8 | `KODE_POS` | string (5 digit) | Kode pos versi CEISA | `96001` | Opsional |
| 9 | `NOMOR_TELPON` | string | Nomor telepon perusahaan (tidak ada di OSS) | `+62-46-100-7923` | Opsional |
| 10 | `KATEGORI` | string (enum) | Kategori pelaku usaha: `IMPORTIR`, `EKSPORTIR`, `KEDUA-DUANYA` | `KEDUA-DUANYA` | Wajib |
| 11 | `NIPER` | string | Nomor Induk Perusahaan (re)Ekspor — fasilitas khusus ekspor, hanya untuk eksportir tertentu | `4803163678` | Kondisional |
| 12 | `NOMOR_API` | string | Nomor Angka Pengenal Importir (versi CEISA) | `1752481353` | Kondisional |
| 13 | `TGL_TERBIT_NIB` | date | Tanggal NIB terbit/terdaftar di CEISA | `2023-07-23` | Wajib |
| 14 | `STATUS_NIB` | string (enum) | Status NIB versi CEISA: `AKTIF`, `DIBEKUKAN`, `DICABUT` — **bisa berbeda dari OSS** | `AKTIF` | Wajib |
| 15 | `KODE_KANTOR` | string | Kode Kantor Bea Cukai pelayanan terakhir | `010100` | Wajib |

## 3. Tabel Pemetaan — Kolom yang Sama Secara Konsep (beda nama/format)

| Konsep | Kolom OSS | Kolom CEISA | Catatan |
|---|---|---|---|
| Identitas perusahaan (matching key) | `NIB` | `NIB` | Primary join key antar sistem |
| NPWP | `NPWP_PERSEROAN` | `NPWP` | Format bisa beda (dengan/tanpa titik-strip) |
| Nama perusahaan | `NAMA_PERSEROAN` | `NAMA_PERUSAHAAN` | Penulisan/singkatan bisa beda |
| Alamat | `ALAMAT_PERSEROAN` | `ALAMAT_PERUSAHAAN` | Format/kelengkapan bisa beda |
| Kelurahan/Kota | `KELURAHAN_PERSEROAN` | `KELURAHAN` | Bisa beda nilai (mis. domisili vs lokasi gudang) |
| Kode wilayah | `PERSEROAN_DAERAH_ID` | `DAERAH_ID` | Idealnya sama, divalidasi ke tabel referensi |
| Kode pos | `KODE_POS_PERSEROAN` | `KODE_POS` | Idealnya sama |
| Status NIB | `STATUS_NIB` | `STATUS_NIB` | **Berpotensi konflik** — sumber update beda waktu |
| Tanggal terkait NIB | `TGL_PERUBAHAN_NIB` | `TGL_TERBIT_NIB` | Beda makna: tanggal *perubahan terakhir* vs tanggal *terbit* |
| Kantor Terdaftar | `KODE_KANTOR` | `KODE_KANTOR` | Referensi KPPBC |

## 4. Kolom Unik per Sumber

**Hanya ada di OSS** (legalitas & fasilitas kepabeanan dari sisi perizinan):
`NAMA_SINGKATAN`, `JENIS_PERSEROAN`, `STATUS_BADAN_HUKUM`, `STATUS_PERSEROAN`, `FLAG_IMPOR`, `FLAG_EKSPOR`, `JENIS_API`, `FLAG_MITA`, `FLAG_AEO`

**Hanya ada di CEISA** (operasional kepabeanan):
`ID_PERUSAHAAN`, `NOMOR_TELPON`, `KATEGORI`, `NIPER`, `NOMOR_API`

## 5. Preview Skema Target — Golden Record

Golden Record menggabungkan kedua sumber per `NIB`, dengan field identitas legal diutamakan dari OSS and field operasional kepabeanan dari CEISA (detail aturan di [`02_business_rules.md`](02_business_rules.md)):

| Field Golden Record | Sumber Diutamakan |
|---|---|
| `NIB` | Matching key (sama di kedua sumber) |
| `NPWP` | OSS (`NPWP_PERSEROAN`) |
| `NAMA_PERUSAHAAN` | OSS (`NAMA_PERSEROAN`) |
| `NAMA_SINGKATAN` | OSS |
| `JENIS_PERSEROAN`, `STATUS_BADAN_HUKUM`, `STATUS_PERSEROAN` | OSS |
| `ALAMAT`, `KELURAHAN`, `DAERAH_ID`, `KODE_POS` | OSS |
| `KODE_KANTOR` | CEISA (Kantor pelayanan aktif) |
| `NOMOR_TELPON` | CEISA (tidak ada di OSS) |
| `KATEGORI`, `NIPER`, `NOMOR_API` | CEISA |
| `FLAG_IMPOR`, `FLAG_EKSPOR` | CEISA (data operasional terkini) |
| `FLAG_MITA`, `FLAG_AEO` | OSS (tidak ada di CEISA) |
| `STATUS_NIB` | Resolusi konflik tanggal terbaru (lihat business rules) |
| `SOURCE` | Penanda asal record: `OSS_CEISA` (matched), `OSS_ONLY`, `CEISA_ONLY` |

Setiap keputusan sumber per field dicatat di `provenance_log.csv` (Tahap 4).
