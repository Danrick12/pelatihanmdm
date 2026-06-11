# Tahap 3 — Duplicate Detection & Matching

**Bobot penilaian**: 20% | **Status**: ⬜ Belum dikerjakan

## Tujuan (sesuai PEDOMAN)

- Exact Matching
- Fuzzy Matching
- Composite Similarity Score
- Duplicate Clustering

## Input

- `data/processed/oss_cleaned.csv`
- `data/processed/ceisa_cleaned.csv` (1 baris per `NIB` — sudah di-dedup data mart di Tahap 2)

## Output

- `reports/candidate_pairs.csv` — pasangan match antara OSS dan CEISA
- `reports/duplicate_cluster.csv` — cluster duplikasi internal (di dalam OSS dan/atau CEISA)

## Breakdown Langkah (notebook section)

> Catatan penting: di referensi (`Data Profiling (1).ipynb`), matching dicari **dalam satu dataset** (cari WP duplikat). Untuk project ini, matching utama dilakukan **antar dua dataset** (OSS vs CEISA), sesuai prioritas di [`../02_business_rules.md`](../02_business_rules.md) §2.

1. Load `oss_cleaned.csv` dan `ceisa_cleaned.csv`
2. **Persiapan matching keys**: `nib_digits` (NIB hanya digit), `npwp_digits` (NPWP hanya digit), `nama_key` (nama dinormalisasi — uppercase, hapus titik/spasi ganda, normalisasi PT/CV)
3. **Exact match — Prioritas 1 (NIB)**: join `oss_cleaned` dan `ceisa_cleaned` pada `nib_digits` → pasangan `match_type=EXACT_NIB`
4. **Exact match — Prioritas 2 (NPWP)**: untuk record yang belum match di langkah 3, join pada `npwp_digits` → `match_type=EXACT_NPWP` (target uji: anomali "NIB Typo" di [`tahap0_simulation_faker.md`](tahap0_simulation_faker.md) §4 — NIB beda tapi NPWP sama)
5. **Fuzzy matching — Prioritas 3**: untuk sisa record yang belum match, hitung similarity `nama_key` (Jaro-Winkler, token sort/set ratio) dan kemiripan alamat (target uji: anomali "Typo Nama" di [`tahap0_simulation_faker.md`](tahap0_simulation_faker.md) §4)
6. **Composite similarity score**: kombinasi weighted dari similarity NPWP (jika ada sebagian match), nama, alamat — sesuai bobot yang akan didefinisikan di notebook
7. **Visualisasi distribusi composite score** + **threshold analysis** (tentukan ambang batas, mis. ≥ 85 dianggap match valid)
8. **Manual spot-check**: tampilkan beberapa contoh pasangan high-score dan borderline untuk validasi visual
9. **Duplicate clustering** (internal per sumber): gunakan `networkx` untuk grouping record yang merujuk entitas sama dalam satu sumber (mis. NIB sama muncul >1 kali di OSS — anomali "Duplicate Entry"). **Catatan**: untuk CEISA, duplikat by `NIB` sudah diselesaikan di Tahap 2 (Data Mart Dedup), jadi clustering CEISA fokus ke kandidat lain (mis. nama/alamat sangat mirip dengan `NIB` berbeda)
10. Export `candidate_pairs.csv` (kolom: `NIB_OSS`, `ID_PERUSAHAAN_CEISA`/`NIB_CEISA`, `match_type`, `similarity_score`) dan `duplicate_cluster.csv` (kolom: `cluster_id`, `source`, `record_id`, `NIB`, `nama`)

> Record yang tidak match sama sekali (tidak masuk `candidate_pairs.csv`) adalah kandidat anomali "Orphan Records" ([`tahap0_simulation_faker.md`](tahap0_simulation_faker.md) §4) — diproses lebih lanjut di Tahap 4 sebagai `SOURCE=OSS_ONLY`/`CEISA_ONLY`.

## Referensi dari `Data Profiling (1).ipynb`

| Cell | Judul | Penggunaan |
|---|---|---|
| 42 | Persiapan Matching Keys | Pola dipakai (normalize_for_matching, extract digits) |
| 43 | Exact Match — NPWP Duplicate | Adaptasi jadi exact match NIB & NPWP antar OSS-CEISA |
| 44 | Exact Match — Kombinasi Multi-Field | Opsional, sebagai cross-check |
| 45-46 | Standard/Sorted Neighbourhood Blocking | Opsional (dataset kecil, blocking mungkin tidak perlu) |
| 47-48 | Eksplorasi String Similarity & Fuzzy Matching Pipeline | Pola dipakai untuk Prioritas 3 |
| 49-51 | Composite Score, Visualisasi, Threshold Analysis | Pola dipakai |
| 52 | Manual Spot-Check | Pola dipakai |
| 53-54 | Duplicate Cluster (Graph Theory) & Visualisasi | Pola dipakai untuk duplikasi internal |
| 55 | Export Laporan Akhir | Pola dipakai |

## Checklist Aktivitas Minimal (PEDOMAN)

- [ ] Exact matching (NIB, NPWP)
- [ ] Fuzzy matching (nama, alamat)
- [ ] Composite similarity score + threshold
- [ ] Duplicate clustering
- [ ] `candidate_pairs.csv` & `duplicate_cluster.csv` ter-generate
