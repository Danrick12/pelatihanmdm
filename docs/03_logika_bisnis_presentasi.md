# Logika Bisnis MDM — Master Data Importir & Eksportir Nasional
### Bahan Tayang — Kelompok 5 (DJBC)

> Dokumen ini merangkum **logika bisnis** project secara end-to-end (kenapa project ini ada, aturan-aturan yang dipakai, dan bagaimana Golden Record terbentuk), disusun per topik agar mudah dipecah jadi slide presentasi. Setiap `---` menandai batas topik/slide. Detail teknis lengkap ada di [`00_overview.md`](00_overview.md), [`01_data_dictionary.md`](01_data_dictionary.md), [`02_business_rules.md`](02_business_rules.md), dan folder [`tahapan/`](tahapan/).

---

## 1. Judul & Konteks Project

- **Tema**: Master Data Management (MDM) — Importir dan Eksportir Nasional
- **Instansi**: Direktorat Jenderal Bea dan Cukai (DJBC)
- **Sumber data**: OSS (Online Single Submission / NIB) + CEISA (Customs-Excise Information System and Automation)
- **Tujuan akhir**: membentuk **Golden Record** — *Single Importer and Exporter View* yang akurat, konsisten, dan terpercaya
- **Fokus masalah yang diselesaikan**:
  - Duplikasi data perusahaan
  - Format NPWP tidak konsisten antar sistem
  - Alamat perusahaan berbeda antar sistem
  - Konflik data legal entity (status NIB OSS vs CEISA)

---

## 2. Latar Belakang Bisnis — Kenapa Project Ini Diperlukan?

**Alur kondisi nyata di lapangan:**

```
   OSS (Pengurusan Izin Usaha)
        │  registrasi / perubahan NIB, status badan hukum, dll.
        ▼
   "System of Record" legalitas — selalu mencerminkan kondisi terkini
        │
        │  ⚠ proses sinkronisasi BERJEDA (tidak real-time)
        ▼
   CEISA (Sistem Operasional Kepabeanan)
        │  dipakai sehari-hari untuk transaksi impor/ekspor
        ▼
   Data CEISA berpotensi "ketinggalan" dari kondisi terkini di OSS
```

- Update di OSS **tidak otomatis** ter-propagate ke CEISA → ada **sync lag**.
- Project ini adalah **rekonsiliasi awal**: membentuk Golden Record dari kondisi data *saat ini* (snapshot), bukan membangun sistem real-time.
- **Implikasi desain utama**:
  1. **OSS = System of Record** untuk field legalitas (identitas, status badan hukum, status NIB, alamat resmi).
  2. **CEISA = sumber operasional** (kantor pelayanan, nomor telepon, fasilitas ekspor/impor aktif).
  3. Indikator risiko langsung dari skenario ini:
     - `HIGH_SYNC_LAG` → `TGL_SYNC_OSS` (CEISA) > 30 hari → kemungkinan ada perubahan OSS yang belum ter-capture.
     - `IS_OUT_OF_SYNC` → `STATUS_NIB` OSS ≠ CEISA → konflik status yang harus diresolusi.
- **Di luar ruang lingkup**: mekanisme *auto-update CEISA via trigger* dari OSS — ini adalah rekomendasi *next step* pengembangan sistem MDM DJBC ke depan.

---

## 3. Dua Sumber Data: Peran & Karakteristik

| | **OSS** | **CEISA** |
|---|---|---|
| **Peran** | Master legalitas / registrasi NIB | Operasional kepabeanan (transaksi impor-ekspor) |
| **Sifat tabel** | Tabel master normal (1 baris = 1 perusahaan) | **Data mart** — bisa >1 baris per `NIB` (snapshot historis pada waktu sinkron berbeda) |
| **Field unggulan** | Identitas legal, status badan hukum, status NIB, alamat resmi, flag impor/ekspor, jenis API | Kategori pelaku usaha, NIPER, nomor API, kode kantor pelayanan, nomor telepon, tanggal sync |
| **Perlakuan dalam Golden Record** | **Trusted source** untuk identitas & legalitas | **Trusted source** untuk data operasional terkini |

> Karena CEISA bersifat data mart, sebelum proses matching, setiap `NIB` di CEISA harus **di-dedup** dengan mengambil baris dengan `TGL_SYNC_OSS` paling baru ("snapshot terbaru").

---

## 4. Skema Data — OSS (16 Kolom)

| Kelompok | Kolom |
|---|---|
| **Identitas** (matching key) | `NIB`, `NPWP_PERSEROAN`, `NAMA_PERSEROAN`, `NAMA_SINGKATAN`, `JENIS_PERSEROAN` |
| **Lokasi** | `ALAMAT_PERSEROAN`, `KELURAHAN_PERSEROAN`, `PERSEROAN_DAERAH_ID`, `KODE_POS_PERSEROAN` |
| **Status** | `STATUS_BADAN_HUKUM`, `STATUS_PERSEROAN`, `STATUS_NIB` |
| **Fasilitas** | `FLAG_IMPOR`, `FLAG_EKSPOR`, `JENIS_API` |
| **Temporal** | `TGL_PERUBAHAN_NIB` (tanggal perubahan/update terakhir di OSS) |

**Contoh nilai kunci:**
- `NIB` → `1043321819600` (13 digit, **matching key utama**)
- `NPWP_PERSEROAN` → `13.389.083.8-637.940` (format baku)
- `STATUS_NIB` → `AKTIF` / `DIBEKUKAN` / `DICABUT`

---

## 5. Skema Data — CEISA (16 Kolom)

| Kelompok | Kolom |
|---|---|
| **Identitas** (untuk matching) | `ID_PERUSAHAAN`, `NIB`, `NPWP`, `NAMA_PERUSAHAAN` |
| **Lokasi** | `ALAMAT_PERUSAHAAN`, `KELURAHAN`, `DAERAH_ID`, `KODE_POS` |
| **Operasional DJBC** | `KATEGORI` (IMPORTIR/EKSPORTIR/KEDUA-DUANYA), `NIPER`, `NOMOR_API`, `KODE_KANTOR`, `NOMOR_TELPON` |
| **Status & Audit** | `STATUS_NIB`, `TGL_TERBIT_NIB`, `TGL_SYNC_OSS` |

**Catatan penting:**
- `NPWP` di CEISA **bisa kotor** (tanpa titik/strip) — anomali yang sengaja disuntikkan untuk diuji di tahap cleansing.
- `TGL_SYNC_OSS` adalah kolom kunci untuk **deteksi sync lag** dan **resolusi snapshot terbaru** (data mart dedup).
- `STATUS_NIB` di CEISA **bisa berbeda** dari OSS → indikasi sync lag / konflik.

---

## 6. Pemetaan Kolom — Konsep yang Sama, Beda Sistem

| Konsep | OSS | CEISA | Catatan Bisnis |
|---|---|---|---|
| Identitas perusahaan | `NIB` | `NIB` | **Primary join key** antar sistem |
| NPWP | `NPWP_PERSEROAN` | `NPWP` | Format bisa beda (dengan/tanpa titik-strip) |
| Nama perusahaan | `NAMA_PERSEROAN` | `NAMA_PERUSAHAAN` | Penulisan/singkatan bisa beda |
| Alamat | `ALAMAT_PERSEROAN` | `ALAMAT_PERUSAHAAN` | Format/kelengkapan bisa beda |
| Kelurahan/Kota | `KELURAHAN_PERSEROAN` | `KELURAHAN` | Bisa beda nilai (domisili vs lokasi gudang) |
| Kode wilayah | `PERSEROAN_DAERAH_ID` | `DAERAH_ID` | Idealnya sama, divalidasi ke tabel referensi |
| Kode pos | `KODE_POS_PERSEROAN` | `KODE_POS` | Idealnya sama |
| Status NIB | `STATUS_NIB` | `STATUS_NIB` | **Berpotensi konflik** — sumber update beda waktu |
| Tanggal terkait NIB | `TGL_PERUBAHAN_NIB` | `TGL_TERBIT_NIB` | Beda makna: *perubahan terakhir* vs *terbit* |

**Kolom unik OSS** (tidak ada di CEISA): `NAMA_SINGKATAN`, `JENIS_PERSEROAN`, `STATUS_BADAN_HUKUM`, `STATUS_PERSEROAN`, `FLAG_IMPOR`, `FLAG_EKSPOR`, `JENIS_API`

**Kolom unik CEISA** (tidak ada di OSS): `ID_PERUSAHAAN`, `NOMOR_TELPON`, `KATEGORI`, `NIPER`, `NOMOR_API`, `KODE_KANTOR`, `TGL_SYNC_OSS`

---

## 7. Fondasi Logika Bisnis: 4 Dimensi Kualitas Data (DMBOK)

Seluruh aturan profiling, cleansing, dan monitoring dipetakan ke **4 dimensi inti**:

| Dimensi | Apa yang Dipastikan | Cara Ukur |
|---|---|---|
| **Kelengkapan (Completeness)** | Field identitas wajib selalu terisi | `NIB`, `NPWP`, `NAMA`, `STATUS_NIB` harus 100% terisi (dijamin di simulasi). Field opsional (`KELURAHAN`, `KODE_POS`, `NOMOR_TELPON`, dll) boleh kosong. |
| **Validitas (Validity)** | Data sesuai format/sintaks resmi | `NIB` = 13 digit numerik; `NPWP` = format `XX.XXX.XXX.X-XXX.XXX`. NPWP "kotor" di CEISA sengaja dipertahankan sebagai kasus uji. |
| **Keunikan (Uniqueness)** | Setiap entitas hanya terwakili sekali | Cek duplikat `NIB`. **Khusus CEISA** (data mart): `NIB` sama dengan baris berbeda = **normal** (snapshot historis) → diselesaikan dengan ambil `TGL_SYNC_OSS` terbaru sebelum matching. |
| **Ketepatan Waktu (Timeliness)** | Data masih relevan & tersinkron | `IS_STALE` = `TGL_PERUBAHAN_NIB` (OSS) > 1 tahun. `HIGH_SYNC_LAG` = `TGL_SYNC_OSS` (CEISA) > 30 hari (SLA sync bulanan). |

> `HIGH_SYNC_LAG` secara langsung merepresentasikan **risiko bisnis**: ada kemungkinan perubahan di OSS (system of record) yang belum sampai ke CEISA.

---

## 8. Strategi Matching Bertingkat (Tahap 3)

Tujuan: menemukan pasangan record OSS ↔ CEISA yang merepresentasikan **perusahaan yang sama**.

| Prioritas | Metode | Confidence | Logika Bisnis |
|---|---|---|---|
| **1** | **Exact Match `NIB`** | 100% | NIB adalah identitas resmi tunggal — jika sama persis, pasti perusahaan yang sama. |
| **2** | **Exact Match `NPWP`** | 95% | Dipakai jika `NIB` tidak match (kemungkinan typo NIB), tapi `NPWP` sama persis. |
| **3** | **Fuzzy Match `NAMA` + `ALAMAT`** | 85% | Untuk sisa record yang tidak match secara identitas numerik — bandingkan kemiripan nama & alamat (threshold similarity ≥ 85). |

**Alur keputusan:**
```
            ┌──────────────────┐
            │  Cocokkan NIB     │──► cocok? ──► EXACT_NIB (100%)
            └──────────────────┘
                     │ tidak cocok
                     ▼
            ┌──────────────────┐
            │  Cocokkan NPWP    │──► cocok? ──► EXACT_NPWP (95%)
            └──────────────────┘
                     │ tidak cocok
                     ▼
            ┌──────────────────────────┐
            │ Fuzzy: Nama + Alamat      │──► skor ≥ 85 ──► FUZZY_MATCH (85%)
            └──────────────────────────┘
                     │ skor < threshold
                     ▼
              ORPHAN (OSS_ONLY / CEISA_ONLY)
```

- Record yang **tidak match sama sekali** → kandidat **"Orphan Records"**, tetap masuk Golden Record sebagai `SOURCE = OSS_ONLY` atau `CEISA_ONLY`.
- Output: `candidate_pairs.csv` (pasangan match) dan `duplicate_cluster.csv` (duplikasi internal per sumber, mis. `NIB` sama muncul >1x di OSS).

---

## 9. Aturan Survivorship — "Siapa yang Menang?" (Tahap 4)

Setelah pasangan OSS-CEISA ditemukan, untuk setiap field harus diputuskan **nilai mana yang dipakai** di Golden Record.

### A. Prinsip Utama

| Kategori Field | Pemenang | Alasan Bisnis |
|---|---|---|
| **Legalitas & Identitas** (nama, NPWP, alamat, status badan hukum, jenis perseroan, flag impor/ekspor) | **OSS** | OSS adalah *System of Record* — mencerminkan kondisi legal terkini hasil pengurusan izin. |
| **Operasional Kepabeanan** (kode kantor pelayanan, nomor telepon, NIPER, nomor API, kategori) | **CEISA** | Data ini hanya ada/terbaru di sistem operasional sehari-hari. |
| **Status NIB** | **"Latest Date Wins"** | Bandingkan tanggal update terakhir di kedua sistem (`TGL_PERUBAHAN_NIB` vs `TGL_TERBIT_NIB`/`TGL_SYNC_OSS`) — status dari sistem yang paling baru diperbarui yang dipakai, sambil tetap menandai konflik. |

### B. Skema Akhir Golden Record

| Field Golden Record | Sumber Diutamakan |
|---|---|
| `NIB` | Matching key (sama di kedua sumber) |
| `NPWP` | OSS |
| `NAMA_PERUSAHAAN`, `NAMA_SINGKATAN` | OSS |
| `JENIS_PERSEROAN`, `STATUS_BADAN_HUKUM`, `STATUS_PERSEROAN` | OSS |
| `ALAMAT`, `KELURAHAN`, `DAERAH_ID`, `KODE_POS` | OSS |
| `KODE_KANTOR` (kantor pelayanan aktif) | CEISA |
| `NOMOR_TELPON` (tidak ada di OSS) | CEISA |
| `KATEGORI`, `NIPER`, `NOMOR_API` | CEISA |
| `FLAG_IMPOR`, `FLAG_EKSPOR` | OSS |
| `STATUS_NIB` | OSS (dengan flag konflik bila beda dari CEISA) |
| `TGL_SYNC_OSS` | CEISA (metadata — dasar cek timeliness) |
| `SOURCE` | `OSS_CEISA` (matched) / `OSS_ONLY` / `CEISA_ONLY` |

> Setiap keputusan sumber per field **dicatat** di `provenance_log.csv` — basis audit & transparansi.

---

## 10. Penandaan Konflik & Risiko (Flag Bisnis Utama)

Tiga *flag* ini adalah **inti logika bisnis** Golden Record — masing-masing merepresentasikan jenis risiko data yang berbeda:

| Flag | Kondisi Trigger | Arti Bisnis |
|---|---|---|
| **`IS_OUT_OF_SYNC`** | `STATUS_NIB` OSS ≠ `STATUS_NIB` CEISA | Status legal perusahaan di OSS sudah berubah (mis. dicabut/dibekukan), tapi CEISA masih mencatat status lama → **risiko transaksi kepabeanan dengan entitas yang sudah tidak valid**. |
| **`IS_STALE`** | `TGL_PERUBAHAN_NIB` (OSS) > 1 tahun dari sekarang | Data legal sudah lama tidak diperbarui — kemungkinan perusahaan tidak aktif/data usang. |
| **`HIGH_SYNC_LAG`** | `TGL_SYNC_OSS` (CEISA) > 30 hari dari sekarang | SLA sinkronisasi bulanan terlampaui — CEISA berpotensi tidak mencerminkan kondisi OSS terkini. |

Ketiga flag ini menjadi dasar untuk:
- Memprioritaskan record mana yang perlu **ditinjau ulang manual** oleh DJBC.
- Mengukur **dimensi Consistency & Timeliness** pada DQ Scorecard (Tahap 5).

---

## 11. Anomali Bisnis yang Disimulasikan & Diuji

Setiap anomali sengaja disuntikkan ke data simulasi (Tahap 0) untuk membuktikan setiap tahap pipeline bekerja:

| # | Anomali | Contoh | Diuji di Tahap |
|---|---|---|---|
| 1 | **Stale Data** | `TGL_PERUBAHAN_NIB` sangat lama (mis. 2015) | Profiling → `IS_STALE` |
| 2 | **Inconsistent NPWP** | CEISA kirim NPWP tanpa titik/strip | Cleansing — standardisasi format |
| 3 | **Fuzzy Identity / Typo Nama** | Nama perusahaan mirip, ada "(TYPO)" atau beda spasi | Fuzzy Matching |
| 4 | **NIB Typo** | Satu digit NIB beda antar sistem | Secondary Matching via NPWP |
| 5 | **Sync Conflict** | `STATUS_NIB` OSS = `DICABUT`, CEISA = `AKTIF` | Survivorship — `IS_OUT_OF_SYNC` |
| 6 | **Logical Conflict** | `FLAG_EKSPOR = N` tapi `NIPER` terisi di CEISA | Business Rule / Consistency Validation |
| 7 | **Orphan Records** | Record hanya ada di OSS atau hanya di CEISA | Golden Record — `SOURCE` tracking |
| 8 | **Missing Optional Field** | `KELURAHAN`, `KODE_POS`, `NOMOR_TELPON` kosong (field wajib selalu terisi) | Completeness Profiling |
| 9 | **Duplicate Entry** | Satu perusahaan muncul 2x di sistem yang sama | Duplicate Detection |
| 10 | **Data Mart Snapshot Duplicate** | `NIB` sama, >1 baris CEISA dengan `NAMA_PERUSAHAAN`/`ALAMAT`/`TGL_SYNC_OSS` berbeda | Pre-matching dedup (ambil snapshot terbaru) |

---

## 12. Pipeline End-to-End — Tahap 0 s.d. 6

```
Tahap 0          Tahap 1         Tahap 2            Tahap 3              Tahap 4              Tahap 5            Tahap 6
Simulasi    ──►  Profiling  ──►  Cleansing &  ──►  Duplicate &     ──►  Golden Record   ──►  DQ Monitoring ──►  Profiling
Data (Faker)     (Before)        Standardization    Matching              & Survivorship       (Scorecard)        (After)
                                  + Data Mart Dedup
```

| Tahap | Fokus Logika Bisnis | Output |
|---|---|---|
| **0 — Simulasi Data** | Membangkitkan ~5.000 entitas + anomali realistis (lihat §11) agar pipeline dapat diuji end-to-end | `oss_nib_data.csv`, `ceisa_data.csv` |
| **1 — Data Profiling (15%)** | Memotret kondisi awal (before): kelengkapan, validitas, duplikasi, baseline skor 4 dimensi DMBOK — **per OSS dan CEISA terpisah** karena skema berbeda | `profiling_before.html` |
| **2 — Cleansing & Standardization (20%)** | Standardisasi nama/alamat/identifier, **Data Mart Dedup CEISA** (1 baris per `NIB`, ambil `TGL_SYNC_OSS` terbaru), penanganan missing value sesuai field wajib/opsional, validasi referensial wilayah | `oss_cleaned.csv`, `ceisa_cleaned.csv`, `dataset_clean.csv`, `audit_trail.csv` |
| **3 — Duplicate Detection & Matching (20%)** | Matching bertingkat OSS↔CEISA (NIB → NPWP → Fuzzy), composite similarity score, clustering duplikasi internal | `candidate_pairs.csv`, `duplicate_cluster.csv` |
| **4 — Golden Record & Survivorship (20%)** | Terapkan aturan survivorship (§9), tandai `IS_OUT_OF_SYNC`/`IS_STALE`/`HIGH_SYNC_LAG`, gabungkan matched + orphan records | `golden_record.csv`, `provenance_log.csv` |
| **5 — Data Quality Monitoring (15%)** | Hitung 5 dimensi (Completeness, Validity, Uniqueness, Consistency, Timeliness) untuk OSS/CEISA (before) vs Golden Record (after) — buktikan peningkatan kualitas | `dq_scorecard.csv` |
| **6 — Profiling Dashboard (10%)** | Re-profiling Golden Record, bandingkan before vs after, tulis insight bisnis & rekomendasi governance | `profiling_after.html` |

---

## 13. Tahap 1 (Profiling) — Logika Bisnis Inti

- Dilakukan **terpisah untuk OSS dan CEISA** karena skema berbeda.
- Duplicate analysis dipecah jadi:
  - **OSS**: duplikat `NIB` = **anomali** (seharusnya unik per sistem).
  - **CEISA**: duplikat `NIB` = **expected** (data mart) → dipisah jadi:
    - *Data Mart Snapshot Duplicate* (normal, snapshot historis)
    - *Duplicate Entry* (baris benar-benar identik = anomali nyata)
- Format validation: `NIB` (13 digit), `NPWP` (format baku), `KODE_POS`, `NOMOR_TELPON`, `STATUS_NIB` (enum).
- Hasil **Baseline DQ Score** (4 dimensi) menjadi **pembanding** untuk Tahap 2 dan 5.

---

## 14. Tahap 2 (Cleansing) — Logika Bisnis Inti

- **Audit trail** wajib ada untuk setiap perubahan (timestamp, operasi, field, jumlah & % terdampak).
- Standardisasi: nama perusahaan (uppercase, normalisasi `PT`/`CV`/`Firma`/`Perum`/`UD`), alamat (title case + singkatan jalan), identifier (`NIB` 13 digit, `NPWP` format baku, `KODE_POS` 5 digit, telepon `+62...`).
- **CEISA Data Mart Dedup** (logika baru/khas project ini): per `NIB`, urutkan berdasarkan `TGL_SYNC_OSS`, ambil baris **terbaru**; baris yang dibuang dicatat di audit trail (`DEDUP_SNAPSHOT`).
- Missing value:
  - Field **wajib** kosong → **flag sebagai data bermasalah**, tidak diisi paksa.
  - Field **opsional** kosong → dibiarkan null dengan justifikasi.
- Validasi referensial kode wilayah (`PERSEROAN_DAERAH_ID` / `DAERAH_ID`).
- **Quality gate** sebelum export: tidak boleh ada `NIB`/`NPWP` invalid lolos tanpa flag.
- Ditutup dengan **perbandingan DQ score before vs after**.

---

## 15. Tahap 3 (Matching) — Logika Bisnis Inti

- Beda dari notebook referensi: matching utama dilakukan **antar dua dataset** (OSS vs CEISA), bukan dalam satu dataset.
- Matching keys disiapkan dulu: `nib_digits`, `npwp_digits`, `nama_key` (ternormalisasi).
- Tiga prioritas matching dijalankan **berurutan** (lihat §8) — record yang sudah match di prioritas atas tidak diproses lagi di prioritas bawah.
- **Composite similarity score**: kombinasi tertimbang dari kemiripan NPWP, nama, dan alamat.
- **Threshold analysis**: menentukan ambang batas (mis. ≥ 85) untuk dianggap match valid, divalidasi dengan **manual spot-check**.
- **Duplicate clustering** (internal per sumber, pakai graph/`networkx`): menemukan record yang merujuk entitas sama dalam satu sumber (anomali "Duplicate Entry").

---

## 16. Tahap 4 (Golden Record) — Logika Bisnis Inti

1. Terapkan `field_rules` (survivorship, §9) ke setiap pasangan match → satu Golden Record + catatan provenance per field.
2. Tandai `IS_OUT_OF_SYNC` jika `STATUS_NIB` OSS ≠ CEISA.
3. Bawa flag `IS_STALE` dan `HIGH_SYNC_LAG` dari Tahap 1/2 (tidak dihitung ulang).
4. Proses **unmatched records** (orphan):
   - Hanya di OSS → `SOURCE = OSS_ONLY`, field CEISA-only kosong.
   - Hanya di CEISA → `SOURCE = CEISA_ONLY`, field OSS-only kosong.
5. **Analisis pola konflik** — insight bisnis: field apa yang paling sering konflik (`STATUS_NIB`, `ALAMAT`, format `NPWP`, `FLAG_EKSPOR` vs `NIPER`).
6. **Provenance analysis** — distribusi sumber per field di Golden Record (berapa % dari OSS vs CEISA vs default).
7. Validasi akhir: `NIB` unik, format `NPWP`/`STATUS_NIB` valid.

---

## 17. Tahap 5 (DQ Monitoring) — Logika Bisnis Inti

Mengukur **5 dimensi** (4 dimensi dasar + Consistency) untuk **3 dataset**: OSS (before), CEISA (before), Golden Record (after).

| Dimensi | Definisi pada Project Ini |
|---|---|
| **Completeness** | Field wajib (`NIB`, `NPWP`, `NAMA`, `STATUS_NIB`) tidak null |
| **Validity** | Format `NIB`, `NPWP`, `KODE_POS`, dan enum (`STATUS_NIB`, `KATEGORI`, `JENIS_PERSEROAN`) sesuai aturan |
| **Uniqueness** | `NIB` unik tanpa duplikat exact — Golden Record dijamin unik per `NIB` |
| **Consistency** | `FLAG_IMPOR` vs `JENIS_API`, `FLAG_EKSPOR` vs `NIPER`/`KATEGORI` konsisten; `STATUS_NIB` OSS = CEISA (diukur via `% IS_OUT_OF_SYNC`) |
| **Timeliness** | `IS_STALE` (OSS) dan `HIGH_SYNC_LAG` (CEISA) |

Output `dq_scorecard.csv` menjadi **bukti kuantitatif** peningkatan kualitas data dari "before" (OSS/CEISA terpisah, banyak inkonsistensi) ke "after" (Golden Record, terkonsolidasi).

---

## 18. Tahap 6 (Profiling Dashboard) — Logika Bisnis Inti

- Re-profiling Golden Record dengan `ydata_profiling` → `profiling_after.html`.
- Bandingkan dengan `profiling_before.html`:
  - Jumlah record (OSS+CEISA sebelum vs Golden Record sesudah, termasuk efek dedup)
  - % missing value sebelum vs sesudah
  - % validity format sebelum vs sesudah
  - Duplikasi sebelum vs sesudah
- **Insight bisnis penutup** + **rekomendasi data governance** (bonus penilaian).

---

## 19. Insight Bisnis & Rekomendasi Data Governance

**Insight kunci yang diharapkan dari pipeline:**
- Persentase record dengan `IS_OUT_OF_SYNC = True` → menunjukkan skala risiko "data CEISA ketinggalan dari OSS".
- Persentase record dengan `HIGH_SYNC_LAG = True` → menunjukkan seberapa sering SLA sinkronisasi bulanan terlampaui.
- Field yang paling sering konflik antar sumber → prioritas perbaikan proses bisnis/sistem.

**Rekomendasi governance (next step, di luar scope Tahap 0-6):**
1. **Auto-update CEISA via trigger dari OSS** — begitu ada perubahan di OSS (status NIB, alamat, dll.), langsung dorong ke CEISA agar sync lag minimal.
2. **Monitoring berkelanjutan** menggunakan logika `dq_scorecard.csv` sebagai dashboard rutin (mis. bulanan, mengikuti SLA sync).
3. **Proses reconciliation periodik** — jalankan ulang pipeline Tahap 2-5 secara berkala agar Golden Record tetap up-to-date.
4. **Standardisasi input di sumber** (OSS & CEISA) untuk mengurangi anomali format (NPWP, nama, alamat) sejak awal — mengurangi beban cleansing di hilir.

---

## 20. Ringkasan Penutup

- **Masalah**: dua sistem (OSS & CEISA) menyimpan data perusahaan yang sama dengan kualitas, format, dan tingkat ke-up-to-date-an berbeda.
- **Solusi**: pipeline MDM 6 tahap — profiling → cleansing → matching → golden record (survivorship) → DQ monitoring → re-profiling.
- **Prinsip kunci**: *OSS menang untuk legalitas, CEISA menang untuk operasional, status NIB pakai latest-date-wins, dan setiap konflik/risiko ditandai secara eksplisit (`IS_OUT_OF_SYNC`, `IS_STALE`, `HIGH_SYNC_LAG`)*.
- **Hasil akhir**: `golden_record.csv` — *Single Importer and Exporter View* yang lebih lengkap, valid, unik, dan konsisten dibanding data sumber, lengkap dengan jejak audit (`audit_trail.csv`, `provenance_log.csv`) dan bukti peningkatan kualitas (`dq_scorecard.csv`, `profiling_before.html` vs `profiling_after.html`).
