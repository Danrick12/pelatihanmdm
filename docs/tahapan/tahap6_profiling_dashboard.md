# Tahap 6 — YData Profiling Dashboard

**Bobot penilaian**: 10% | **Status**: ✅ Selesai

## Tujuan (sesuai PEDOMAN)

Melakukan profiling ulang terhadap Golden Record yang dihasilkan, sebagai pembanding terhadap profiling awal (Tahap 1).

## Input

- `data/golden/golden_record.csv`
- `reports/profiling_before.html` (pembanding)

## Output

- `reports/profiling_after.html` (via `ydata_profiling`)

## Breakdown Langkah (notebook section)

1. Load `golden_record.csv`
2. Jalankan `ydata_profiling.ProfileReport` terhadap golden record → simpan sebagai `reports/profiling_after.html`
3. **Bandingkan ringkasan profiling_before vs profiling_after**:
   - Jumlah record (OSS + CEISA sebelum vs golden record sesudah — termasuk pengurangan akibat dedup)
   - Missing value % sebelum vs sesudah
   - Format validity % sebelum vs sesudah
   - Duplikasi sebelum vs sesudah
4. Tulis **insight bisnis** penutup: ringkasan perbaikan kualitas data hasil MDM, rekomendasi data governance (mengacu ke "Bonus Penilaian" PEDOMAN — anomali bisnis menarik, risiko kualitas data, rekomendasi implementasi data governance)

## Referensi dari `Data Profiling (1).ipynb`

Tidak ada cell yang langsung sesuai — notebook referensi menggunakan laporan HTML custom (cell 95: "Generate Laporan HTML Otomatis") untuk DQ monitoring, bukan `ydata_profiling` untuk re-profiling. Tahap 6 ini adalah **section baru**, dibangun dari awal menggunakan `ydata_profiling` sesuai requirement eksplisit PEDOMAN ("Membuat laporan profiling menggunakan YData Profiling").

## Checklist Aktivitas Minimal (PEDOMAN)

- [x] `profiling_after.html` ter-generate dari golden record
- [x] Perbandingan before vs after didokumentasikan
- [x] Insight bisnis & rekomendasi data governance ditulis (bonus penilaian)
