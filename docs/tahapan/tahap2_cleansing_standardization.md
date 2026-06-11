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
- `data/processed/ceisa_cleaned.csv`
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
5. **Penanganan missing value** sesuai mandatory fields di [`../02_business_rules.md`](../02_business_rules.md) §3:
   - Field wajib kosong → flag sebagai data bermasalah (tidak diisi paksa, dicatat di audit trail)
   - Field opsional kosong (`NAMA_SINGKATAN`, `KODE_POS`, `NOMOR_TELPON`, `NIPER`/`NOMOR_API`) → biarkan null dengan justifikasi (memang tidak relevan untuk perusahaan tsb)
6. **Validasi referensial**: cek `PERSEROAN_DAERAH_ID` (OSS) dan `DAERAH_ID` (CEISA) terhadap tabel kode wilayah referensi; flag jika kode tidak dikenal
7. **Quality gate**: pemeriksaan otomatis sebelum export — pastikan tidak ada NIB invalid format, NPWP invalid format lolos tanpa flag
8. Export `oss_cleaned.csv`, `ceisa_cleaned.csv`, gabungkan jadi `dataset_clean.csv`, dan simpan `audit_trail.csv`
9. **Perbandingan DQ score before vs after** (bandingkan dengan baseline Tahap 1)

> Cell "Deteksi & Penanganan Outlier (IQR/Winsorizing)" di referensi **kemungkinan tidak relevan** (data kita minim kolom numerik kontinu) — diganti/diskip dengan cek konsistensi flag (`FLAG_IMPOR` vs `JENIS_API`, `FLAG_EKSPOR` vs `NIPER`/`KATEGORI`) yang sudah didefinisikan sebagai anomali di business rules §4.

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

## Checklist Aktivitas Minimal (PEDOMAN)

- [ ] Standardisasi nama (OSS & CEISA)
- [ ] Standardisasi alamat (OSS & CEISA)
- [ ] Standardisasi identifier — NIB, NPWP, kode pos, telepon
- [ ] Penanganan missing value
- [ ] Validasi referensial (kode wilayah)
- [ ] Audit trail tercatat & diekspor
- [ ] `dataset_clean.csv` & `audit_trail.csv` ter-generate
