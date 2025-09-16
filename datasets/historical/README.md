# WSE Indices Historical Dataset

Complete historical dataset of Warsaw Stock Exchange indices composition.

## Dataset Overview

- **Generated**: 2025-09-16
- **Records**: 29,378
- **Date Range**: 2007_03_16 to 2024_06_21
- **Indices**: MWIG40, SWIG80, SWIG80*, WIG, WIG20, WIG30
- **Companies**: 669

## Files

### Current Dataset (20250916)

- **`wse_complete_historical_20250916.sqlite`** - SQLite database (recommended)
- **`wse_complete_historical_20250916.xlsx`** - Multi-sheet Excel file
- **`wse_complete_historical_20250916.csv`** - Complete CSV export
- **`wse_complete_historical_20250916.json`** - JSON format
- **`wse_complete_historical_20250916_summary.txt`** - Detailed statistics

## Usage Examples

### SQLite Database

```python
import sqlite3
import pandas as pd

# Connect to database
conn = sqlite3.connect('wse_complete_historical_20250916.sqlite')

# Get all WIG records for 2024
df = pd.read_sql_query("""
    SELECT * FROM stock_records 
    WHERE index_name = 'WIG' AND date LIKE '2024%'
    ORDER BY date, share_percent DESC
""", conn)

# Get summary statistics
summary = pd.read_sql_query("SELECT * FROM summary_by_index", conn)
print(summary)
```

### Pandas CSV

```python
import pandas as pd

# Load complete dataset
df = pd.read_csv('wse_complete_historical_20250916.csv')

# Filter for specific index and date
wig20_latest = df[(df['Index_Name'] == 'WIG20') & (df['Date'] == df['Date'].max())]
```

## Data Schema

Each record contains:

- **date**: Date in YYYY_MM_DD format
- **index_name**: Index identifier (WIG, WIG20, WIG30, mWIG40, sWIG80)
- **no**: Sequential number in the index
- **isin**: International Securities Identification Number
- **company_name**: Company name
- **price_pln**: Stock price in Polish Złoty
- **number_of_shares**: Number of shares in the index
- **share_percent**: Weight percentage in the index
