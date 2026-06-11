# Business Rules — Matching, Survivorship, Validity & Anomali (DJBC)

Dokumen ini adalah spec final untuk implementasi MDM Kelompok 5. Mengacu pada [`01_data_dictionary.md`](../01_data_dictionary.md).

## 1. Matching Strategy (Tahap 3)

Matching dilakukan antar **OSS** dan **CEISA** secara berjenjang:

| Prioritas | Metode | Field Kunci | Kondisi |
|---|---|---|---|
| 1 | Exact Match | `NIB` (13 digit) | Join utama. NIB harus dinormalisasi (hanya angka). |
| 2 | Exact Match | `NPWP` (15 digit) | Jika NIB tidak match (kemungkinan typo NIB). |
| 3 | Fuzzy Match | `NAMA` + `ALAMAT` | Jika identitas angka gagal. Threshold similarity ≥ 85. |

## 2. Survivorship Rules (Tahap 4)

Menentukan data mana yang masuk ke **Golden Record** jika terjadi perbedaan antar sistem.

| Kelompok | Field | Pemenang | Alasan Bisnis |
|---|---|---|---|
| **Legalitas** | `NAMA`, `NPWP`, `ALAMAT`, `JENIS_PERSEROAN`, `STATUS_WP` | **OSS** | OSS adalah otoritas pendaftaran badan usaha nasional. |
| **Status NIB** | `STATUS_NIB` | **OSS** | OSS adalah *system of record* NIB. Perbedaan di CEISA dianggap *stale data*. |
| **Operasional** | `KATEGORI`, `NIPER`, `NOMOR_API`, `KODE_KANTOR` | **CEISA** | CEISA merekam aktivitas pelayanan dan kategori terkini di lapangan. |
| **Fasilitas** | `FLAG_MITA`, `FLAG_AEO`, `FLAG_UMK` | **OSS** | Fasilitas ini diterbitkan di level profil pusat (OSS). |
| **Kontak** | `NOMOR_TELPON` | **CEISA** | OSS sering tidak memiliki data kontak operasional. |

## 3. Validity Rules (Tahap 1, 2, 5)

Standar kualitas yang harus dipenuhi:
- **NIB**: Wajib 13 digit numerik.
- **NPWP**: Wajib format `XX.XXX.XXX.X-XXX.XXX`.
- **Status NIB**: Harus salah satu dari `{AKTIF, DIBEKUKAN, DICABUT}`.
- **Flag**: Harus `{Y, N}`.
- **Kode Kantor**: Harus ada di `KPPBC_LIST` (6 digit).

## 4. Anomali Bisnis yang Disimulasikan (Tahap 0)

Script generator (`03.1generator.py`) wajib menyuntikkan 7 jenis anomali ini:

1. **Inkonsistensi NPWP**: CEISA mengirim NPWP tanpa titik/strip (kotor), OSS bersih.
2. **Fuzzy Name**: Perbedaan penulisan PT (depan vs belakang) atau typo ringan di CEISA.
3. **NIB Typo**: NIB di CEISA salah 1 digit, memaksa sistem menggunakan matching NPWP.
4. **CEISA Out-of-Sync**: `STATUS_NIB` OSS = 'DICABUT', tapi CEISA masih 'AKTIF'.
5. **Logic Violation**: `NIPER` terisi (perusahaan ekspor) tapi `FLAG_EKSPOR` = 'N'.
6. **Orphan Records**: Data yang hanya ada di OSS (belum transaksi) atau hanya di CEISA (data lama).
7. **Missing Contacts**: Kolom telepon atau email kosong di salah satu sistem.

## 5. Konflik Status & "Out-of-Sync" Indicator
Jika `STATUS_NIB` di OSS dan CEISA berbeda, Golden Record akan mengambil nilai **OSS**, namun field **`IS_OUT_OF_SYNC`** akan diset menjadi `True`. Ini adalah *insight* penting bagi DJBC untuk melakukan rekonsiliasi sistem.

---
**Status:** *Final Specification for Kelompok 5*
