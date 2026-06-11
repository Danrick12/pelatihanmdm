# MDM Mini Project — Kelompok 5 (DJBC): Master Data Importir & Eksportir Nasional

## 1. Konteks Project

Mengacu pada `reference/PEDOMAN MINI PROJECT MDM 2026.pdf`, Kelompok 5 (DJBC) mengerjakan:

- **Tema**: Master Data Importir dan Eksportir Nasional
- **Sumber data simulasi**: CEISA, OSS (NIB)
- **Fokus permasalahan**: duplikasi perusahaan, format NPWP tidak konsisten, alamat perusahaan berbeda antar sistem, konflik data legal entity
- **Target Golden Record**: Single Importer and Exporter View

Gaya pengerjaan & teknik mengikuti `reference/Data Profiling (1).ipynb` (referensi kelompok lain — Master Data Wajib Pajak), tapi datanya diganti OSS + CEISA dan disesuaikan aturan bisnis Kelompok 5.

## 2. Dokumen Pendukung

| Dokumen | Isi |
|---|---|
| [`01_data_dictionary.md`](01_data_dictionary.md) | Pemetaan kolom OSS vs CEISA: sama, beda, unik |
| [`02_business_rules.md`](02_business_rules.md) | Aturan matching, survivorship, validity, anomali bisnis |
| [`tahapan/tahap1_data_profiling.md`](tahapan/tahap1_data_profiling.md) | Detail Tahap 1 — Data Profiling |
| [`tahapan/tahap2_cleansing_standardization.md`](tahapan/tahap2_cleansing_standardization.md) | Detail Tahap 2 — Cleansing & Standardization |
| [`tahapan/tahap3_duplicate_matching.md`](tahapan/tahap3_duplicate_matching.md) | Detail Tahap 3 — Duplicate Detection & Matching |
| [`tahapan/tahap4_golden_record.md`](tahapan/tahap4_golden_record.md) | Detail Tahap 4 — Golden Record & Survivorship |
| [`tahapan/tahap5_dq_monitoring.md`](tahapan/tahap5_dq_monitoring.md) | Detail Tahap 5 — Data Quality Monitoring |
| [`tahapan/tahap6_profiling_dashboard.md`](tahapan/tahap6_profiling_dashboard.md) | Detail Tahap 6 — YData Profiling Dashboard |

> **Di luar ruang lingkup**: Lab "API & Data Integration" (FastAPI/ngrok/webhook) di `Data Profiling (1).ipynb` tidak termasuk Tahap 1-6 PEDOMAN — tidak dikerjakan kecuali sebagai bonus opsional jika waktu tersisa.

## 3. Rencana Struktur Folder (target akhir)

```
reference/      <- PEDOMAN PDF, Data Profiling (1).ipynb (acuan gaya & teknik)
docs/           <- dokumen perencanaan ini
  tahapan/
data/
  raw/          <- oss_nib_data.csv, ceisa_data.csv (regenerasi sesuai data_dictionary)
  processed/    <- oss_cleaned.csv, ceisa_cleaned.csv, dataset_clean.csv
  golden/       <- golden_record.csv
notebooks/
  Mini_Project_Kelompok_5_DJBC.ipynb   <- notebook utama, dibangun bertahap
scripts/        <- script pendukung (regenerasi data dll, ditulis ulang)
reports/        <- audit_trail.csv, candidate_pairs.csv, duplicate_cluster.csv,
                   provenance_log.csv, dq_scorecard.csv,
                   profiling_before.html, profiling_after.html
archive/        <- file-file lama hasil eksperimen sebelumnya
```

> Reorganisasi folder (pemindahan file lama ke `archive/` & `reference/`) sudah dieksekusi (Step 0 selesai).

## 4. Roadmap & Status

| Step | Deskripsi | Output | Bobot | Status |
|---|---|---|---|---|
| 0 | Rapikan struktur folder (archive file lama) | struktur folder baru | - | ✅ Selesai |
| 1 | Data dictionary OSS vs CEISA | `01_data_dictionary.md` | - | ✅ Selesai |
| 2 | Business rules (matching, survivorship, validity) | `02_business_rules.md` | - | ✅ Selesai |
| 3 | Regenerasi data simulasi OSS & CEISA | `data/raw/oss_nib_data.csv`, `data/raw/ceisa_data.csv` | - | ⬜ Belum |
| 4 | Tahap 1 — Data Profiling | `profiling_before.html` | 15% | ⬜ Belum |
| 5 | Tahap 2 — Cleansing & Standardization | `dataset_clean.csv`, `audit_trail.csv` | 20% | ⬜ Belum |
| 6 | Tahap 3 — Duplicate Detection & Matching | `candidate_pairs.csv`, `duplicate_cluster.csv` | 20% | ⬜ Belum |
| 7 | Tahap 4 — Golden Record & Survivorship | `golden_record.csv`, `provenance_log.csv` | 20% | ⬜ Belum |
| 8 | Tahap 5 — Data Quality Monitoring | `dq_scorecard.csv` | 15% | ⬜ Belum |
| 9 | Tahap 6 — YData Profiling Dashboard | `profiling_after.html` | 10% | ⬜ Belum |

Setiap step dikerjakan satu per satu, dengan checkpoint review bareng sebelum lanjut ke step berikutnya.
