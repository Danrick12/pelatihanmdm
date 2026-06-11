# [TAHAP 5] DATA QUALITY MONITORING
# Berdasarkan: docs/tahapan/tahap5_dq_monitoring.md & docs/02_business_rules.md §1, §4
#
# Quality Rules Engine sederhana (rule_id, dimension, field, check, severity) dijalankan
# pada 3 dataset: OSS (before), CEISA (before), Golden Record (after) - lalu dibandingkan
# dalam satu scorecard per dimensi DMBOK (Completeness, Validity, Uniqueness, Consistency,
# Timeliness) untuk menunjukkan peningkatan kualitas data hasil MDM.

import pandas as pd
import re
from dataclasses import dataclass
from typing import Callable

from Source.step02_reference import STATUS_NIB_POOL, JENIS_PERSEROAN_POOL, KATEGORI_CEISA_POOL
from Source.step07_matching import DUMMY_NIB

NIB_PATTERN = re.compile(r'^\d{13}$')
NPWP_PATTERN = re.compile(r'^\d{2}\.\d{3}\.\d{3}\.\d{1}-\d{3}\.\d{3}$')
KODE_POS_PATTERN = re.compile(r'^\d{5}$')

DIMENSIONS = ['Completeness', 'Validity', 'Uniqueness', 'Consistency', 'Timeliness']


@dataclass
class QualityRule:
    rule_id: str
    dimension: str
    field: str
    description: str
    check: Callable[[pd.DataFrame], pd.Series]  # df -> bool Series (True = pass)
    severity: str  # HIGH / MEDIUM / LOW


@dataclass
class RuleResult:
    dataset: str
    rule_id: str
    dimension: str
    field: str
    description: str
    severity: str
    total: int
    n_pass: int
    n_fail: int
    pass_rate: float


# --- Quality Rules Engine: check builders (Langkah 2) ---

def _to_digit_str(series):
    """KODE_POS terbaca float64 (mis. 1330.0) - konversi ke string digit tanpa '.0'
    agar panjang digit (utk cek format 5-digit) tetap apa adanya (leading zero yang
    hilang akibat tipe numerik akan terdeteksi sebagai format tidak valid)."""
    def conv(x):
        if pd.isna(x):
            return None
        if isinstance(x, float) and x.is_integer():
            return str(int(x))
        return str(x)
    return series.apply(conv)


def check_completeness(field):
    """Field wajib (NIB/NPWP/NAMA/STATUS_NIB) tidak boleh null/kosong."""
    def _check(df):
        col = df[field]
        return col.notna() & (col.astype(str).str.strip() != '')
    return _check


def check_format(field, pattern, numeric=False):
    """Field opsional/format: nilai kosong dianggap PASS (itu isu Completeness, bukan
    Validity), nilai yang terisi harus cocok dengan pattern."""
    def _check(df):
        col = _to_digit_str(df[field]) if numeric else df[field]
        is_null = col.isna()
        match = col.astype(str).str.match(pattern)
        return is_null | match
    return _check


def check_not_dummy_nib(df):
    """NIB tidak boleh nilai dummy/kosong "0000000000000" (anomali NIB Invalid - Dummy/Kosong)."""
    return df['NIB'].astype(str) != DUMMY_NIB


def check_enum(field, pool):
    """Nilai field (jika terisi) harus termasuk dalam pool referensi yang sah."""
    def _check(df):
        col = df[field]
        return col.isna() | col.isin(pool)
    return _check


def check_unique_nib(df):
    """NIB unik secara internal - kecuali NIB dummy "0000000000000" yang secara sah
    dimiliki banyak entitas berbeda (lihat tahap4_golden_record.md langkah 8)."""
    nib = df['NIB'].astype(str)
    is_dummy = nib == DUMMY_NIB
    is_dup = nib.duplicated(keep=False)
    return ~(is_dup & ~is_dummy)


def check_flag_impor_jenis_api(df):
    """FLAG_IMPOR='Y' -> JENIS_API harus terisi; FLAG_IMPOR='N' -> JENIS_API harus kosong."""
    flag = df['FLAG_IMPOR']
    jenis_filled = df['JENIS_API'].notna() & (df['JENIS_API'].astype(str).str.strip() != '')
    return flag.isna() | ((flag == 'Y') & jenis_filled) | ((flag == 'N') & ~jenis_filled)


def check_kategori_niper(df):
    """KATEGORI='IMPORTIR' -> NIPER harus kosong; KATEGORI EKSPORTIR/KEDUA-DUANYA -> NIPER
    harus terisi (anomali "Logical Conflict")."""
    kategori = df['KATEGORI']
    niper_filled = df['NIPER'].notna() & (df['NIPER'].astype(str).str.strip() != '')
    return (
        kategori.isna()
        | ((kategori == 'IMPORTIR') & ~niper_filled)
        | (kategori.isin(['EKSPORTIR', 'KEDUA-DUANYA']) & niper_filled)
    )


def check_flag_is_false(field):
    """Flag boolean (IS_STALE/HIGH_SYNC_LAG/IS_OUT_OF_SYNC/IS_LOGICAL_CONFLICT_NIPER) harus
    False. NaN (flag tidak relevan utk record ybs, mis. OSS_ONLY tanpa HIGH_SYNC_LAG)
    dianggap PASS (tidak berlaku)."""
    def _check(df):
        col = df[field].apply(lambda x: bool(x) if pd.notna(x) else False)
        return ~col
    return _check


# --- Definisi rules per dataset (Langkah 3) ---

OSS_RULES = [
    QualityRule('COMP-NIB', 'Completeness', 'NIB', 'NIB tidak boleh kosong',
                check_completeness('NIB'), 'HIGH'),
    QualityRule('COMP-NPWP', 'Completeness', 'NPWP_PERSEROAN', 'NPWP tidak boleh kosong',
                check_completeness('NPWP_PERSEROAN'), 'HIGH'),
    QualityRule('COMP-NAMA', 'Completeness', 'NAMA_PERSEROAN', 'NAMA tidak boleh kosong',
                check_completeness('NAMA_PERSEROAN'), 'HIGH'),
    QualityRule('COMP-STATUS_NIB', 'Completeness', 'STATUS_NIB', 'STATUS_NIB tidak boleh kosong',
                check_completeness('STATUS_NIB'), 'HIGH'),

    QualityRule('VAL-NIB-FORMAT', 'Validity', 'NIB', 'NIB harus 13 digit numerik',
                check_format('NIB', NIB_PATTERN), 'HIGH'),
    QualityRule('VAL-NIB-DUMMY', 'Validity', 'NIB', 'NIB tidak boleh dummy "0000000000000"',
                check_not_dummy_nib, 'MEDIUM'),
    QualityRule('VAL-NPWP-FORMAT', 'Validity', 'NPWP_PERSEROAN', 'NPWP harus format XX.XXX.XXX.X-XXX.XXX',
                check_format('NPWP_PERSEROAN', NPWP_PATTERN), 'HIGH'),
    QualityRule('VAL-KODE_POS-FORMAT', 'Validity', 'KODE_POS_PERSEROAN', 'KODE_POS (jika terisi) harus 5 digit',
                check_format('KODE_POS_PERSEROAN', KODE_POS_PATTERN, numeric=True), 'LOW'),
    QualityRule('VAL-STATUS_NIB-ENUM', 'Validity', 'STATUS_NIB', f'STATUS_NIB harus salah satu dari {STATUS_NIB_POOL}',
                check_enum('STATUS_NIB', STATUS_NIB_POOL), 'HIGH'),
    QualityRule('VAL-JENIS_PERSEROAN-ENUM', 'Validity', 'JENIS_PERSEROAN', f'JENIS_PERSEROAN harus salah satu dari {JENIS_PERSEROAN_POOL}',
                check_enum('JENIS_PERSEROAN', JENIS_PERSEROAN_POOL), 'MEDIUM'),

    QualityRule('UNIQ-NIB', 'Uniqueness', 'NIB', 'NIB unik (di luar NIB dummy)',
                check_unique_nib, 'HIGH'),

    QualityRule('CONS-FLAG_IMPOR-JENIS_API', 'Consistency', 'FLAG_IMPOR/JENIS_API',
                'FLAG_IMPOR konsisten dengan pengisian JENIS_API',
                check_flag_impor_jenis_api, 'MEDIUM'),

    QualityRule('TIME-IS_STALE', 'Timeliness', 'IS_STALE', 'TGL_PERUBAHAN_NIB tidak boleh > 1 tahun (IS_STALE)',
                check_flag_is_false('IS_STALE'), 'MEDIUM'),
]

CEISA_RULES = [
    QualityRule('COMP-NIB', 'Completeness', 'NIB', 'NIB tidak boleh kosong',
                check_completeness('NIB'), 'HIGH'),
    QualityRule('COMP-NPWP', 'Completeness', 'NPWP', 'NPWP tidak boleh kosong',
                check_completeness('NPWP'), 'HIGH'),
    QualityRule('COMP-NAMA', 'Completeness', 'NAMA_PERUSAHAAN', 'NAMA tidak boleh kosong',
                check_completeness('NAMA_PERUSAHAAN'), 'HIGH'),
    QualityRule('COMP-STATUS_NIB', 'Completeness', 'STATUS_NIB', 'STATUS_NIB tidak boleh kosong',
                check_completeness('STATUS_NIB'), 'HIGH'),

    QualityRule('VAL-NIB-FORMAT', 'Validity', 'NIB', 'NIB harus 13 digit numerik',
                check_format('NIB', NIB_PATTERN), 'HIGH'),
    QualityRule('VAL-NIB-DUMMY', 'Validity', 'NIB', 'NIB tidak boleh dummy "0000000000000"',
                check_not_dummy_nib, 'MEDIUM'),
    QualityRule('VAL-NPWP-FORMAT', 'Validity', 'NPWP', 'NPWP harus format XX.XXX.XXX.X-XXX.XXX (anomali Inconsistent NPWP)',
                check_format('NPWP', NPWP_PATTERN), 'HIGH'),
    QualityRule('VAL-KODE_POS-FORMAT', 'Validity', 'KODE_POS', 'KODE_POS (jika terisi) harus 5 digit',
                check_format('KODE_POS', KODE_POS_PATTERN, numeric=True), 'LOW'),
    QualityRule('VAL-STATUS_NIB-ENUM', 'Validity', 'STATUS_NIB', f'STATUS_NIB harus salah satu dari {STATUS_NIB_POOL}',
                check_enum('STATUS_NIB', STATUS_NIB_POOL), 'HIGH'),
    QualityRule('VAL-KATEGORI-ENUM', 'Validity', 'KATEGORI', f'KATEGORI harus salah satu dari {KATEGORI_CEISA_POOL}',
                check_enum('KATEGORI', KATEGORI_CEISA_POOL), 'MEDIUM'),

    QualityRule('UNIQ-NIB', 'Uniqueness', 'NIB', 'NIB unik (1 baris per NIB - data mart sudah di-dedup Tahap 2)',
                check_unique_nib, 'HIGH'),

    QualityRule('CONS-KATEGORI-NIPER', 'Consistency', 'KATEGORI/NIPER',
                'KATEGORI konsisten dengan pengisian NIPER (anomali Logical Conflict)',
                check_kategori_niper, 'MEDIUM'),

    QualityRule('TIME-HIGH_SYNC_LAG', 'Timeliness', 'HIGH_SYNC_LAG', 'TGL_SYNC_OSS tidak boleh > 30 hari (HIGH_SYNC_LAG)',
                check_flag_is_false('HIGH_SYNC_LAG'), 'MEDIUM'),
]

GOLDEN_RULES = [
    QualityRule('COMP-NIB', 'Completeness', 'NIB', 'NIB tidak boleh kosong',
                check_completeness('NIB'), 'HIGH'),
    QualityRule('COMP-NPWP', 'Completeness', 'NPWP', 'NPWP tidak boleh kosong',
                check_completeness('NPWP'), 'HIGH'),
    QualityRule('COMP-NAMA', 'Completeness', 'NAMA', 'NAMA tidak boleh kosong',
                check_completeness('NAMA'), 'HIGH'),
    QualityRule('COMP-STATUS_NIB', 'Completeness', 'STATUS_NIB', 'STATUS_NIB tidak boleh kosong',
                check_completeness('STATUS_NIB'), 'HIGH'),

    QualityRule('VAL-NIB-FORMAT', 'Validity', 'NIB', 'NIB harus 13 digit numerik',
                check_format('NIB', NIB_PATTERN), 'HIGH'),
    QualityRule('VAL-NIB-DUMMY', 'Validity', 'NIB', 'NIB tidak boleh dummy "0000000000000"',
                check_not_dummy_nib, 'MEDIUM'),
    QualityRule('VAL-NPWP-FORMAT', 'Validity', 'NPWP', 'NPWP harus format XX.XXX.XXX.X-XXX.XXX',
                check_format('NPWP', NPWP_PATTERN), 'HIGH'),
    QualityRule('VAL-KODE_POS-FORMAT', 'Validity', 'KODE_POS', 'KODE_POS (jika terisi) harus 5 digit',
                check_format('KODE_POS', KODE_POS_PATTERN, numeric=True), 'LOW'),
    QualityRule('VAL-STATUS_NIB-ENUM', 'Validity', 'STATUS_NIB', f'STATUS_NIB harus salah satu dari {STATUS_NIB_POOL}',
                check_enum('STATUS_NIB', STATUS_NIB_POOL), 'HIGH'),
    QualityRule('VAL-JENIS_PERSEROAN-ENUM', 'Validity', 'JENIS_PERSEROAN', f'JENIS_PERSEROAN harus salah satu dari {JENIS_PERSEROAN_POOL}',
                check_enum('JENIS_PERSEROAN', JENIS_PERSEROAN_POOL), 'MEDIUM'),
    QualityRule('VAL-KATEGORI-ENUM', 'Validity', 'KATEGORI', f'KATEGORI harus salah satu dari {KATEGORI_CEISA_POOL}',
                check_enum('KATEGORI', KATEGORI_CEISA_POOL), 'MEDIUM'),

    QualityRule('UNIQ-NIB', 'Uniqueness', 'NIB', 'NIB unik (di luar NIB dummy - lihat tahap4 langkah 8)',
                check_unique_nib, 'HIGH'),

    QualityRule('CONS-FLAG_IMPOR-JENIS_API', 'Consistency', 'FLAG_IMPOR/JENIS_API',
                'FLAG_IMPOR konsisten dengan pengisian JENIS_API',
                check_flag_impor_jenis_api, 'MEDIUM'),
    QualityRule('CONS-KATEGORI-NIPER', 'Consistency', 'KATEGORI/NIPER',
                'KATEGORI konsisten dengan pengisian NIPER (anomali Logical Conflict)',
                check_kategori_niper, 'MEDIUM'),
    QualityRule('CONS-STATUS_NIB-SYNC', 'Consistency', 'IS_OUT_OF_SYNC',
                'STATUS_NIB OSS & CEISA harus sinkron (anomali Sync Conflict)',
                check_flag_is_false('IS_OUT_OF_SYNC'), 'HIGH'),
    QualityRule('CONS-FLAG_EKSPOR-NIPER', 'Consistency', 'IS_LOGICAL_CONFLICT_NIPER',
                'FLAG_EKSPOR konsisten dengan NIPER (anomali Logical Conflict)',
                check_flag_is_false('IS_LOGICAL_CONFLICT_NIPER'), 'HIGH'),

    QualityRule('TIME-IS_STALE', 'Timeliness', 'IS_STALE', 'TGL_PERUBAHAN_NIB tidak boleh > 1 tahun (IS_STALE)',
                check_flag_is_false('IS_STALE'), 'MEDIUM'),
    QualityRule('TIME-HIGH_SYNC_LAG', 'Timeliness', 'HIGH_SYNC_LAG', 'TGL_SYNC_OSS tidak boleh > 30 hari (HIGH_SYNC_LAG)',
                check_flag_is_false('HIGH_SYNC_LAG'), 'MEDIUM'),
]


# --- Eksekusi rules (Langkah 4) ---

def run_rules(df, rules, dataset_name):
    results = []
    total = len(df)
    for rule in rules:
        mask = rule.check(df)
        n_pass = int(mask.sum())
        results.append(RuleResult(
            dataset=dataset_name, rule_id=rule.rule_id, dimension=rule.dimension,
            field=rule.field, description=rule.description, severity=rule.severity,
            total=total, n_pass=n_pass, n_fail=total - n_pass,
            pass_rate=(n_pass / total * 100) if total else 0.0,
        ))
    return results


def print_rule_results(results):
    for r in results:
        status = 'PASS' if r.pass_rate == 100 else ('WARN' if r.pass_rate >= 95 else 'FAIL')
        print(f'   [{status}] {r.rule_id:<26} {r.dimension:<13} | {r.pass_rate:6.2f}% '
              f'({r.n_pass:,}/{r.total:,}) | {r.description}')


# --- Scorecard perbandingan before vs after (Langkah 5) ---

def build_scorecard(df_results):
    pivot = df_results.groupby(['dimension', 'dataset'])['pass_rate'].mean().unstack('dataset')
    pivot = pivot.reindex(DIMENSIONS)[['OSS', 'CEISA', 'GOLDEN']]
    pivot.loc['Overall'] = pivot.mean(axis=0)

    scorecard = pivot.reset_index().rename(columns={
        'dimension': 'dimension', 'OSS': 'oss_score', 'CEISA': 'ceisa_score', 'GOLDEN': 'golden_score',
    })
    scorecard['delta_vs_oss'] = scorecard['golden_score'] - scorecard['oss_score']
    scorecard['delta_vs_ceisa'] = scorecard['golden_score'] - scorecard['ceisa_score']
    return scorecard


if __name__ == "__main__":
    print('=' * 60)
    print('TAHAP 5: DATA QUALITY MONITORING')
    print('=' * 60)

    # Langkah 1: Load data
    df_oss = pd.read_csv('data/processed/oss_cleaned.csv', dtype={'NIB': str, 'NPWP_PERSEROAN': str})
    df_ceisa = pd.read_csv('data/processed/ceisa_cleaned.csv', dtype={'NIB': str, 'NPWP': str})
    df_golden = pd.read_csv('data/golden/golden_record.csv', dtype={'NIB': str, 'NPWP': str})
    print(f'\n1. Load data: OSS={len(df_oss):,} baris, CEISA={len(df_ceisa):,} baris, '
          f'Golden Record={len(df_golden):,} baris')

    # Langkah 2-3: Quality Rules Engine + definisi rules per dimensi
    print(f'\n2-3. Quality Rules Engine terdefinisi: '
          f'OSS={len(OSS_RULES)} rules, CEISA={len(CEISA_RULES)} rules, Golden={len(GOLDEN_RULES)} rules')
    print(f'     5 dimensi DMBOK: {", ".join(DIMENSIONS)}')

    # Langkah 4: Eksekusi rules untuk 3 dataset
    print('\n4. Eksekusi rules...')
    results_oss = run_rules(df_oss, OSS_RULES, 'OSS')
    results_ceisa = run_rules(df_ceisa, CEISA_RULES, 'CEISA')
    results_golden = run_rules(df_golden, GOLDEN_RULES, 'GOLDEN')
    df_results = pd.DataFrame([r.__dict__ for r in results_oss + results_ceisa + results_golden])

    print(f'\n   --- OSS (Before, {len(df_oss):,} baris) ---')
    print_rule_results(results_oss)
    print(f'\n   --- CEISA (Before, {len(df_ceisa):,} baris) ---')
    print_rule_results(results_ceisa)
    print(f'\n   --- Golden Record (After, {len(df_golden):,} baris) ---')
    print_rule_results(results_golden)

    # Langkah 5: Scorecard perbandingan before vs after
    print('\n5. Scorecard perbandingan (Before vs After)...')
    df_scorecard = build_scorecard(df_results)
    print('\n' + df_scorecard.to_string(index=False, float_format=lambda x: f'{x:6.2f}'))

    # Langkah 6: Export
    df_scorecard.to_csv('reports/dq_scorecard.csv', index=False)
    df_results.to_csv('reports/dq_rule_results.csv', index=False)
    print('\n6. Export hasil...')
    print(f'   reports/dq_scorecard.csv     -> {len(df_scorecard):,} baris (skor per dimensi)')
    print(f'   reports/dq_rule_results.csv  -> {len(df_results):,} baris (detail per rule)')

    overall = df_scorecard[df_scorecard['dimension'] == 'Overall'].iloc[0]
    print('\n' + '=' * 60)
    print('RINGKASAN OVERALL DQ SCORE')
    print('=' * 60)
    print(f'OSS (Before)          : {overall["oss_score"]:.2f}/100')
    print(f'CEISA (Before)        : {overall["ceisa_score"]:.2f}/100')
    print(f'Golden Record (After) : {overall["golden_score"]:.2f}/100')
    print(f'Peningkatan vs OSS    : {overall["delta_vs_oss"]:+.2f} poin')
    print(f'Peningkatan vs CEISA  : {overall["delta_vs_ceisa"]:+.2f} poin')
    print('=' * 60)
