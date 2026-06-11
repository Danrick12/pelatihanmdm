# Tahap 1 — Data Profiling

**Bobot penilaian**: 15% | **Status**: ⬜ Belum dikerjakan

## Tujuan (sesuai PEDOMAN)

- Dataset overview
- Statistik deskriptif
- Missing value analysis
- Duplicate analysis
- Format validation
- Baseline Data Quality Score

## Input

- `data/raw/oss_nib_data.csv` (hasil Step 3)
- `data/raw/ceisa_data.csv` (hasil Step 3)

## Output

- `reports/profiling_before.html` (via `ydata_profiling`)
- Ringkasan profiling tertulis di notebook (insight awal sebelum cleansing)

## Breakdown Langkah (notebook section)

Dilakukan **untuk OSS dan CEISA secara terpisah** (dua dataset, dua skema berbeda — lihat [`../01_data_dictionary.md`](../01_data_dictionary.md)):

1. Setup & load `oss_nib_data.csv` dan `ceisa_data.csv`
2. **Dataset overview**: shape, dtype per kolom, jumlah null & %, jumlah unique, head/tail — untuk masing-masing dataset
3. **Statistik deskriptif**: kolom numerik (NIB, KODE_POS, dll — describe + range) dan kolom kategorik (value_counts top values) — masing-masing dataset
4. **Missing value analysis**: tabel jumlah & persentase missing per kolom + severity (OK/LOW/MEDIUM/HIGH/CRITICAL), visualisasi bar chart + `missingno` matrix
5. **Duplicate analysis**:
   - Full duplicate (semua kolom identik)
   - **OSS**: Duplicate by `NIB` — harusnya unik per sistem (anomali jika ada)
   - **CEISA**: Duplicate by `NIB` — *expected* (CEISA bersifat data mart, lihat dimensi "Unik" di [`../02_business_rules.md`](../02_business_rules.md)). Pisahkan jadi:
     - **Data Mart Snapshot Duplicate**: `NIB` sama, `NAMA_PERUSAHAAN`/`ALAMAT_PERUSAHAAN`/`TGL_SYNC_OSS` berbeda → normal (snapshot historis), ambil baris dengan `TGL_SYNC_OSS` terbaru sebagai preview dedup untuk Tahap 2/3
     - **Duplicate Entry**: baris benar-benar identik → anomali (lihat Section 5 #6 di business rules)
   - Duplicate by nama perusahaan (kandidat duplikasi entitas)
6. **Format validation** sesuai [`../02_business_rules.md`](../02_business_rules.md) §3 (Validity Rules): cek `NIB` (13 digit), `NPWP`/`NPWP_PERSEROAN` (format baku), `KODE_POS`, `NOMOR_TELPON` (CEISA), `STATUS_NIB` (enum valid)
7. **Baseline Data Quality Score**: hitung 4 dimensi DMBOK — Completeness, Validity, Uniqueness, **Timeliness** — untuk OSS dan CEISA sesuai [`../02_business_rules.md`](../02_business_rules.md) §1, termasuk `IS_STALE` (`TGL_PERUBAHAN_NIB`, OSS) dan `HIGH_SYNC_LAG` (`TGL_SYNC_OSS`, CEISA). Skor "before" jadi pembanding di Tahap 2 & 5.
8. **YData Profiling report**: jalankan `ydata_profiling.ProfileReport` untuk OSS dan CEISA, gabungkan/simpan sebagai `reports/profiling_before.html`

## Referensi dari `Data Profiling (1).ipynb`

| Cell | Judul | Penggunaan |
|---|---|---|
| 8 | Inspeksi Awal Dataset | Pola dipakai, di-loop untuk OSS & CEISA |
| 9 | Statistik Deskriptif | Pola dipakai |
| 10 | Deteksi Kolom Duplikat | Pola dipakai |
| 11-12 | Analisis & Visualisasi Missing Values | Pola dipakai |
| 13-14 | Exact Duplicate Detection & Visualisasi | Adaptasi: duplicate by NIB / nama |
| 15-16 | Validasi Format NPWP, NIK, Telepon, Email | Adaptasi field sesuai skema OSS/CEISA |
| 17-18 | Data Quality Scorecard & Visualisasi | Pola dipakai sebagai baseline — **catatan**: `Source/step05_profiling.py` masih versi 6 dimensi (Akurasi & Konsistensi hardcode 100%), perlu disederhanakan jadi 4 dimensi sesuai `02_business_rules.md` |
| - | **ydata-profiling** | **Belum ada di referensi — cell baru** |

## Checklist Aktivitas Minimal (PEDOMAN)

- [ ] Dataset overview (OSS & CEISA)
- [ ] Statistik deskriptif (OSS & CEISA)
- [ ] Missing value analysis (OSS & CEISA)
- [ ] Duplicate analysis (OSS & CEISA)
- [ ] Format validation (OSS & CEISA)
- [ ] Baseline Data Quality Score (OSS & CEISA)
- [ ] `profiling_before.html` ter-generate
