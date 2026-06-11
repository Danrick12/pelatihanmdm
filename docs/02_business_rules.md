# Business Rules — Matching, Survivorship, Validity & DMBOK Dimensions (DJBC)

Dokumen ini adalah spesifikasi final yang mengintegrasikan standar **DMBOK** yang telah disederhanakan untuk fokus Mini Project Kelompok 5.

## 1. Dimensi Kualitas Data (4 Core Dimensions)

Setiap aturan pada sistem profiling dipetakan ke 4 dimensi utama:

| Dimensi | Implementasi pada Proyek DJBC | Parameter Ukur |
|---|---|---|
| **Kelengkapan** | Memastikan semua informasi identitas wajib tersedia. | Null check pada `NIB`, `NPWP`, `NAMA`, `STATUS_NIB` — dijamin 100% (validasi wajib di input/generator). Field opsional (`KELURAHAN`, `KODE_POS`, `NOMOR_TELPON`, dll) tetap bisa kosong. |
| **Validitas** | Memastikan data sesuai dengan sintaks/format resmi. | Regex check `NIB` (13 digit) & `NPWP` (format `XX.XXX.XXX.X-XXX.XXX`). Anomali NPWP kotor (tanpa separator) di CEISA tetap dipertahankan sebagai kasus uji (lihat Section 5 #2). |
| **Unik** | Memastikan setiap entitas hanya terwakili satu kali. | Duplicate check pada kolom `NIB` internal sistem. CEISA bersifat *data mart* — `NIB` yang sama bisa muncul di >1 baris dengan `NAMA_PERUSAHAAN`/`ALAMAT_PERUSAHAAN` berbeda (snapshot waktu berbeda). Resolusi: ambil baris dengan `TGL_SYNC_OSS` terbaru sebelum proses matching (lihat Section 5 anomali "Data Mart Snapshot Duplicate"). |
| **Ketepatan Waktu** | Memastikan data tetap relevan dan tersinkronisasi. | *OSS Staleness*: `TGL_PERUBAHAN_NIB` > 1 tahun dari sekarang → `IS_STALE = True`. *Sync Lag*: `TGL_SYNC_OSS` (CEISA) > 30 hari dari sekarang → `HIGH_SYNC_LAG = True` (SLA sync CEISA-OSS bulanan). |

> **Catatan konteks bisnis**: `HIGH_SYNC_LAG` merepresentasikan risiko bahwa perubahan di OSS (system of record) belum ter-propagate ke CEISA — lihat latar belakang bisnis di [`00_overview.md`](00_overview.md).

## 2. Matching Strategy (Tahap 3)

| Prioritas | Metode | Confidence Score | Keterangan |
|---|---|---|---|
| 1 | Exact Match `NIB` | 100% | Identitas utama resmi. |
| 2 | Exact Match `NPWP` | 95% | Digunakan jika NIB typo namun NPWP sama. |
| 3 | Fuzzy Match `NAMA` + `ALAMAT` | 85% | Threshold similarity ≥ 85. |

## 3. Survivorship & Business Logic (Tahap 4)

### A. Aturan Pemenang (Survivorship)
- **Legalitas & Status:** OSS Menang (sebagai *System of Record*). 
- **Operasional:** CEISA Menang (termasuk `KODE_KANTOR` dan `NOMOR_TELPON`).

### B. Aturan Ketepatan Waktu (Timeliness Detail)
- **Data Staleness:** Jika `TGL_PERUBAHAN` > 1 tahun dari sekarang, record ditandai `IS_STALE = True`.
- **Sync Lag:** Jika selisih tanggal update OSS dan CEISA > 30 hari, ditandai sebagai `HIGH_SYNC_LAG`.

## 4. Validity Rules (Tahap 1, 2, 5)

- **NIB:** Wajib 13 digit numerik.
- **NPWP:** Wajib format `XX.XXX.XXX.X-XXX.XXX`.

## 5. Anomali Bisnis yang Disimulasikan (Tahap 0)

1. **Stale Data:** Tanggal perubahan NIB sangat lama (mis: 2015).
2. **Inconsistent NPWP:** CEISA mengirim NPWP tanpa titik/strip.
3. **Fuzzy Identity:** Nama mirip tapi NIB beda sedikit.
4. **Sync Conflict:** Status di OSS 'DICABUT' tapi di CEISA 'AKTIF'.
5. **Missing Optional Field:** Field opsional (`KELURAHAN`, `KODE_POS`, `NOMOR_TELPON`, dll) kosong — field wajib (`NIB`, `NPWP`, `NAMA`, `STATUS_NIB`) selalu terisi.
6. **Duplicate Entry:** Satu perusahaan muncul 2 kali di sistem yang sama.
7. **Data Mart Snapshot Duplicate:** `NIB` yang sama muncul di >1 baris CEISA dengan `NAMA_PERUSAHAAN`/`ALAMAT_PERUSAHAAN` dan `TGL_SYNC_OSS` berbeda (representasi snapshot historis data mart).

---
**Status:** *Final 4-Dimension DMBOK Specification*
