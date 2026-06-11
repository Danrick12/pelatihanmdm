# Tahap 4 — Golden Record & Survivorship

**Bobot penilaian**: 20% | **Status**: ⬜ Belum dikerjakan

## Tujuan (sesuai PEDOMAN)

- Menentukan survivorship rules
- Menentukan trusted source
- Menangani conflict resolution
- Membentuk Golden Record

## Input

- `data/processed/oss_cleaned.csv`
- `data/processed/ceisa_cleaned.csv`
- `reports/candidate_pairs.csv` (hasil Tahap 3)

## Output

- `data/golden/golden_record.csv`
- `reports/provenance_log.csv`

## Breakdown Langkah (notebook section)

1. Load `oss_cleaned.csv`, `ceisa_cleaned.csv`, `candidate_pairs.csv`
2. **Definisi survivorship rules**: implementasikan tabel di [`../02_business_rules.md`](../02_business_rules.md) §2 sebagai `field_rules` dict (field → sumber menang / rule khusus)
3. **Fungsi `create_golden_record()`**: untuk satu pasangan match (OSS row + CEISA row), terapkan `field_rules` → hasilkan satu golden record + catatan provenance per field; isi kolom `IS_OUT_OF_SYNC = True` jika `STATUS_NIB` OSS ≠ CEISA
4. **Proses semua matched pairs** (`EXACT_NIB`, `EXACT_NPWP`, `FUZZY` di atas threshold) → batch golden record generation
5. **Proses unmatched records**:
   - NIB hanya ada di OSS → masuk golden record apa adanya, `SOURCE=OSS_ONLY`, field CEISA-only kosong
   - NIB hanya ada di CEISA → masuk golden record apa adanya, `SOURCE=CEISA_ONLY`, field OSS-only kosong
6. **Analisis pola konflik**: rekap field mana yang paling sering konflik antar OSS-CEISA (mis. `STATUS_NIB`, `ALAMAT`, `NPWP` format) — insight bisnis
7. **Provenance analysis**: tabel distribusi sumber per field (berapa % field di golden record berasal dari OSS vs CEISA vs default)
8. **Quality validation golden record**: pastikan `NIB` unik (drop duplicate keep first jika masih ada), format `NPWP`/`STATUS_NIB` valid sesuai validity rules
9. Export `golden_record.csv` dan `provenance_log.csv`

> Cell "Simulasi Dataset Sumber 1 & 2" (SIDJP/e-Filing) di referensi **tidak diperlukan** — OSS dan CEISA kita memang sudah dua sumber data asli, tidak perlu disimulasikan dari satu dataset. Cell "Workflow Resolusi Konflik Manual" (`ConflictResolver`) bersifat **opsional** — bisa disederhanakan jadi log konflik otomatis tanpa workflow interaktif.

## Referensi dari `Data Profiling (1).ipynb`

| Cell | Judul | Penggunaan |
|---|---|---|
| 58-59 | Simulasi Dataset Sumber 1 & 2 | **Tidak dipakai** — OSS/CEISA sudah 2 sumber asli |
| 60 | Definisi Survivorship Rules | Pola dipakai, isi sesuai business_rules §2 |
| 61-63 | Combine Data, Fungsi Merger, Batch Generation | Pola dipakai |
| 64 | Analisis Pola Konflik | Pola dipakai |
| 65 | Workflow Resolusi Konflik Manual | Opsional — bisa disederhanakan |
| 66 | Provenance Analysis | Pola dipakai |
| 67 | Quality Validation Golden Record | Pola dipakai |
| 68 | Export Output | Pola dipakai |
| 69 | Visualisasi Pipeline MDM End-to-End | Opsional, bagus untuk presentasi |

## Checklist Aktivitas Minimal (PEDOMAN)

- [ ] Survivorship rules terdefinisi & terdokumentasi
- [ ] Trusted source per field jelas (OSS vs CEISA)
- [ ] Deteksi & pencatatan `STATUS_NIB` out-of-sync (CEISA vs OSS) diterapkan
- [ ] Golden record terbentuk (matched + OSS_ONLY + CEISA_ONLY)
- [ ] `golden_record.csv` & `provenance_log.csv` ter-generate
