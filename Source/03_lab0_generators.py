# [LAB 0.2] GENERATOR IDENTIFIER DJBC
import random
from datetime import datetime, timedelta

def generate_nib_valid():
    """Generate NIB 13 digit numerik sesuai standar OSS"""
    return ''.join([str(random.randint(0, 9)) for _ in range(13)])

def generate_nib_invalid():
    """Generate NIB bermasalah untuk simulasi anomali"""
    error_types = [
        lambda: ''.join([str(random.randint(0, 9)) for _ in range(12)]), # Kurang digit
        lambda: ''.join([str(random.randint(0, 9)) for _ in range(13)]) + 'X', # Ada huruf
        lambda: '0000000000000' # Dummy/Kosong
    ]
    return random.choice(error_types)()

def generate_npwp_valid():
    """Generate NPWP format baku: XX.XXX.XXX.X-XXX.XXX (15 digit)"""
    d = [str(random.randint(0,99)).zfill(2), str(random.randint(0,999)).zfill(3), 
         str(random.randint(0,999)).zfill(3), str(random.randint(0,9)),
         str(random.randint(0,999)).zfill(3), str(random.randint(0,999)).zfill(3)]
    return f"{d[0]}.{d[1]}.{d[2]}.{d[3]}-{d[4]}.{d[5]}"

def generate_npwp_invalid():
    """Generate NPWP kotor (tanpa separator/salah format)"""
    raw_15 = ''.join([str(random.randint(0, 9)) for _ in range(15)])
    error_types = [
        lambda: raw_15, # Tanpa titik/strip (sering di CEISA)
        lambda: f"{raw_15[:9]}", # Digit kurang
        lambda: raw_15.replace('0', 'O').replace('1', 'I'), # Typo karakter mirip
        lambda: f"{raw_15[:2]} {raw_15[2:5]} {raw_15[5:8]}" # Pake spasi
    ]
    return random.choice(error_types)()

def generate_api_valid():
    """Generate Nomor API (10 digit numerik)"""
    return ''.join([str(random.randint(0, 9)) for _ in range(10)])

def generate_niper_valid():
    """Generate Nomor NIPER (10 digit numerik)"""
    return ''.join([str(random.randint(0, 9)) for _ in range(10)])

def generate_date_random(start_year=2020, end_year=2025):
    """Generate tanggal acak dalam format string YYYY-MM-DD"""
    start_date = datetime(start_year, 1, 1)
    end_date = datetime(end_year, 12, 31)
    time_between_dates = end_date - start_date
    days_between_dates = time_between_dates.days
    random_days = random.randrange(days_between_dates)
    return (start_date + timedelta(days=random_days)).strftime('%Y-%m-%d')
