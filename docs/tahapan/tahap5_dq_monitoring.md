# Tahap 5 — Data Quality Monitoring

**Bobot penilaian**: 15% | **Status**: ⬜ Belum dikerjakan

## Tujuan (sesuai PEDOMAN)

Mengukur dimensi kualitas data:
- Completeness
- Validity
- Uniqueness
- Consistency
- Timeliness

## Input

- `data/processed/oss_cleaned.csv`
- `data/processed/ceisa_cleaned.csv` (1 baris per `NIB` — sudah di-dedup data mart di Tahap 2)
- `data/golden/golden_record.csv`

## Output

- `reports/dq_scorecard.csv`

## Breakdown Langkah (notebook section)

1. Load `oss_cleaned.csv`, `ceisa_cleaned.csv`, `golden_record.csv`
2. **Quality Rules Engine** (versi sederhana, adaptasi `QualityRule`/`RuleResult` dari referensi): setiap rule punya `rule_id`, `dimension`, `field`, kondisi pass/fail, severity
3. **Definisi rules per dimensi**, mengacu 4 dimensi DMBOK di [`../02_business_rules.md`](../02_business_rules.md) §1 dan validity rules di §4:
   - **Completeness**: mandatory fields tidak boleh null (`NIB`, `NPWP`, `NAMA`, `STATUS_NIB`)
   - **Validity**: format `NIB` (13 digit), `NPWP` (format baku), `KODE_POS` (5 digit), `STATUS_NIB`/`KATEGORI`/`JENIS_PERSEROAN` sesuai enum
   - **Uniqueness**: `NIB` unik, tidak ada duplikat exact — `oss_cleaned`/`ceisa_cleaned` masih bisa mengandung sisa anomali "Duplicate Entry" ([`tahap0_simulation_faker.md`](tahap0_simulation_faker.md) §4), sedangkan `golden_record` dijamin unik per `NIB` (lihat [`tahap4_golden_record.md`](tahap4_golden_record.md) langkah 8)
   - **Consistency**: `FLAG_IMPOR` konsisten dengan `JENIS_API` terisi; `FLAG_EKSPOR` konsisten dengan `NIPER`/`KATEGORI` (anomali "Logical Conflict", [`tahap0_simulation_faker.md`](tahap0_simulation_faker.md) §4); `STATUS_NIB` OSS vs CEISA harus sama — jika beda, ditandai `IS_OUT_OF_SYNC = True` (anomali "Konflik Status", lihat [`tahap4_golden_record.md`](tahap4_golden_record.md) langkah 3 dan latar belakang bisnis di [`../00_overview.md`](../00_overview.md) §1). Pada Golden Record, metrik ini dihitung langsung dari `% IS_OUT_OF_SYNC = True`
   - **Timeliness**: gunakan `IS_STALE` (OSS, `TGL_PERUBAHAN_NIB` > 1 tahun) dan `HIGH_SYNC_LAG` (CEISA, `TGL_SYNC_OSS` > 30 hari) sesuai [`../02_business_rules.md`](../02_business_rules.md) §1 — pada `golden_record`, kedua flag dibawa dari Tahap 1/2 (lihat [`tahap4_golden_record.md`](tahap4_golden_record.md) langkah 3)
4. **Eksekusi rules** untuk tiga dataset: OSS (before), CEISA (before), Golden Record (after)
5. **Scorecard perbandingan**: tabel skor per dimensi & overall, before (OSS/CEISA) vs after (Golden) — menunjukkan peningkatan kualitas hasil MDM
6. Export `dq_scorecard.csv`

> Bagian **Great Expectations**, **multi-level alerting**, **simulasi time series 30 hari**, dan **export Power BI** di referensi **diskip** — di luar ruang lingkup Tahap 1-6 PEDOMAN dan Power BI eksplisit "tidak wajib".

## Referensi dari `Data Profiling (1).ipynb`

| Cell | Judul | Penggunaan |
|---|---|---|
| 87 | Quality Rules Engine (framework) | Pola dipakai (disederhanakan) |
| 88 | Definisi 15 Quality Rules | Adaptasi field & dimensi sesuai OSS/CEISA/Golden |
| 89 | Eksekusi Rules & Analisis Hasil | Pola dipakai |
| 90-92 | Great Expectations, Multi-level Alerting | **Diskip** |
| 93-94 | Simulasi & Visualisasi DQ Time Series | **Diskip** |
| 96 | Export Power BI | **Diskip** |

## Checklist Aktivitas Minimal (PEDOMAN)

- [ ] Completeness terukur (OSS, CEISA, Golden)
- [ ] Validity terukur
- [ ] Uniqueness terukur
- [ ] Consistency terukur
- [ ] Timeliness terukur
- [ ] `dq_scorecard.csv` ter-generate (before vs after)
