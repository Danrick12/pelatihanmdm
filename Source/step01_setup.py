# ============================================================
# CELL 1: INSTALL LIBRARY TAMBAHAN
# Jalankan cell ini pertama kali sebelum cell lainnya
# Estimasi waktu: 30-60 detik
# ============================================================

# Install missingno untuk visualisasi missing values
import subprocess
subprocess.check_call(['pip', 'install', 'missingno', '-q'])

# Install faker untuk generate data simulasi
subprocess.check_call(['pip', 'install', 'faker', '-q'])

# Install ydata-profiling untuk laporan profiling Tahap 1 & Tahap 6
subprocess.check_call(['pip', 'install', 'ydata-profiling', '-q'])

# Konfirmasi instalasi berhasil
print('✅ Instalasi library selesai!')
print('Library yang tersedia:')
print('  - pandas       : manipulasi dan analisis data')
print('  - numpy        : komputasi numerik')
print('  - faker        : generate data simulasi realistis')
print('  - matplotlib   : visualisasi dasar')
print('  - seaborn      : visualisasi statistik')
print('  - missingno    : visualisasi missing values')


# ============================================================
# CELL 2: IMPORT SEMUA LIBRARY
# ============================================================

import pandas as pd               # manipulasi dataframe
import numpy as np                # komputasi numerik
import re                         # regular expression untuk validasi format
import random                     # random number generator
import warnings
warnings.filterwarnings('ignore') # sembunyikan warning yang tidak penting

# Faker untuk generate data simulasi
from faker import Faker
from faker.providers import person, address, company, internet, phone_number

# Visualisasi
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import missingno as msno

# Setting tampilan
pd.set_option('display.max_columns', None)     # tampilkan semua kolom
pd.set_option('display.max_rows', 50)          # max 50 baris ditampilkan
pd.set_option('display.float_format', '{:.2f}'.format)  # 2 desimal
pd.set_option('display.width', 120)

# Setting style visualisasi
sns.set_theme(style='whitegrid', palette='Blues_d')
plt.rcParams['figure.figsize'] = (12, 5)
plt.rcParams['font.family']    = 'sans-serif'

# Set seed agar data yang dihasilkan konsisten
RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

print('✅ Semua library berhasil diimport!')
print(f'   Pandas versi  : {pd.__version__}')
print(f'   NumPy versi   : {np.__version__}')

