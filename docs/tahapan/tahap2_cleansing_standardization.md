# Tahap 2 — Data Cleansing & Standardization

**Bobot penilaian**: 20% | **Status**: ⬜ Belum dikerjakan

## Tujuan (sesuai PEDOMAN)

- Standardisasi nama
- Standardisasi alamat
- Standardisasi identifier
- Penanganan missing value
- Validasi referensial
- Audit trail perubahan

## Input

- `data/raw/oss_nib_data.csv`
- `data/raw/ceisa_data.csv`
- `reports/profiling_before.html` (insight Tahap 1 jadi acuan prioritas cleansing)

## Output

- `data/processed/oss_cleaned.csv`
- `data/processed/ceisa_cleaned.csv` (1 baris per `NIB` — sudah di-dedup dari snapshot data mart, ambil `TGL_SYNC_OSS` terbaru)
- `data/processed/dataset_clean.csv` (gabungan/union OSS+CEISA dengan kolom `SOURCE`, untuk deliverable PEDOMAN)
- `reports/audit_trail.csv` (gabungan log OSS + CEISA)

## Breakdown Langkah (notebook section)

Dijalankan **per dataset** (OSS dan CEISA), masing-masing punya `AuditTrail` sendiri lalu digabung di akhir:

1. Setup class `AuditTrail` (catat: timestamp, operation, field, n_affected, pct_affected, description)
2. **Standardisasi nama**: `NAMA_PERSEROAN` (OSS) / `NAMA_PERUSAHAAN` (CEISA) — uppercase, normalisasi prefix `PT`/`CV`/`Firma`/`Perum`/`UD`, hapus karakter aneh
3. **Standardisasi alamat**: `ALAMAT_PERSEROAN` / `ALAMAT_PERUSAHAAN` — title case, normalisasi singkatan (Jl., No., dll)
4. **Standardisasi identifier**:
   - `NIB`: pastikan 13 digit, hanya angka
   - `NPWP_PERSEROAN` / `NPWP`: format ke baku `XX.XXX.XXX.X-XXX.XXX`
   - `KODE_POS` / `KODE_POS_PERSEROAN`: 5 digit
   - `NOMOR_TELPON` (CEISA): normalisasi ke format `+62...`
5. **CEISA Data Mart Dedup**: per `NIB`, jika ada >1 baris (snapshot berbeda — lihat dimensi "Unik" di [`../02_business_rules.md`](../02_business_rules.md) §1), urutkan berdasarkan `TGL_SYNC_OSS` dan ambil baris terbaru saja. Baris yang dibuang dicatat di audit trail (operation: `DEDUP_SNAPSHOT`, jumlah baris terbuang per `NIB`). Hasilnya: `ceisa_cleaned.csv` punya 1 baris per `NIB`.
6. **Penanganan missing value** sesuai mandatory fields di [`../02_business_rules.md`](../02_business_rules.md) §1 (dimensi Kelengkapan):
   - Field wajib (`NIB`, `NPWP`/`NPWP_PERSEROAN`, `NAMA_PERSEROAN`/`NAMA_PERUSAHAAN`, `STATUS_NIB`) kosong → flag sebagai data bermasalah (tidak diisi paksa, dicatat di audit trail)
   - Field opsional kosong (`NAMA_SINGKATAN`, `KELURAHAN`/`KELURAHAN_PERSEROAN`, `KODE_POS`/`KODE_POS_PERSEROAN`, `NOMOR_TELPON`, `NIPER`/`NOMOR_API`) → biarkan null dengan justifikasi (memang tidak relevan untuk perusahaan tsb)
7. **Validasi referensial**: cek `PERSEROAN_DAERAH_ID` (OSS) dan `DAERAH_ID` (CEISA) terhadap tabel kode wilayah referensi; flag jika kode tidak dikenal
8. **Quality gate**: pemeriksaan otomatis sebelum export — pastikan tidak ada NIB invalid format, NPWP invalid format lolos tanpa flag
9. Export `oss_cleaned.csv`, `ceisa_cleaned.csv` (CEISA: 1 baris per `NIB` setelah dedup), gabungkan jadi `dataset_clean.csv`, dan simpan `audit_trail.csv`
10. **Perbandingan DQ score before vs after** (bandingkan dengan baseline Tahap 1)

> Cell "Deteksi & Penanganan Outlier (IQR/Winsorizing)" di referensi **kemungkinan tidak relevan** (data kita minim kolom numerik kontinu) — diganti/diskip dengan cek konsistensi flag (`FLAG_IMPOR` vs `JENIS_API`, `FLAG_EKSPOR` vs `NIPER`/`KATEGORI`), yaitu anomali "Logical Conflict" yang terdaftar di tabel anomali [`tahap0_simulation_faker.md`](tahap0_simulation_faker.md) §4.
>
> **Catatan gap terpisah**: "Logical Conflict" — bersama "NIB Typo" dan "Orphan Records" — adalah 3 anomali di tabel `tahap0_simulation_faker.md` (10 item) yang belum punya entri eksplisit di daftar 7 anomali `02_business_rules.md` §5. Penyelarasan (apakah §5 perlu diekspansi jadi 10 item) dibahas terpisah, belum diputuskan.

## Referensi dari `Data Profiling (1).ipynb`

| Cell | Judul | Penggunaan |
|---|---|---|
| 23 | Sistem Audit Trail | Pakai langsung (class `AuditTrail`) |
| 24 | Standardisasi Nama | Pola dipakai |
| 25-26 | Standardisasi Alamat | Pola dipakai |
| 27 | Standardisasi Format NPWP | Pola dipakai |
| 28-29 | Standardisasi NIK, Telepon, Email | Adaptasi: NIK tidak relevan, fokus telepon (CEISA) |
| 30 | Handling Missing Values | Pola dipakai, strategi sesuai mandatory fields |
| 31-32 | Validasi Referensial | Adaptasi: kode wilayah OSS/CEISA |
| 33-34 | Deteksi & Penanganan Outlier | Kemungkinan diskip/diganti cek konsistensi flag |
| 36 | Quality Gate | Pola dipakai |
| 37 | Export Clean Dataset & Audit Trail | Pola dipakai |
| 38 | Perbandingan DQ Score Before vs After | Pola dipakai |
| - | **CEISA Data Mart Dedup** | **Belum ada di referensi — logic baru** (ambil baris `TGL_SYNC_OSS` terbaru per `NIB`) |

## Checklist Aktivitas Minimal (PEDOMAN)

- [ ] Standardisasi nama (OSS & CEISA)
- [ ] Standardisasi alamat (OSS & CEISA)
- [ ] Standardisasi identifier — NIB, NPWP, kode pos, telepon
- [ ] CEISA data mart dedup (1 baris per `NIB`, ambil `TGL_SYNC_OSS` terbaru)
- [ ] Penanganan missing value
- [ ] Validasi referensial (kode wilayah)
- [ ] Audit trail tercatat & diekspor
- [ ] `dataset_clean.csv` & `audit_trail.csv` ter-generate
