# WSE Indices Weights Loader

A Python tool for downloading and parsing PDF files containing stock index composition data from the Warsaw Stock Exchange (WSE) via the GPW Benchmark website. This tool extracts structured data about stocks, their weights, prices, and shares from index composition PDFs.

## Features

### v0.2 - Multi-Index Support
- **Multi-Index Processing**: Download and process ALL available indices (WIG, WIG20, WIG30, mWIG40, sWIG80) across all historical dates
- **Consolidated Excel Reports**: Multi-sheet Excel files with separate sheets per date and consolidated views
- **Advanced Data Discovery**: Automatically discovers all available PDFs from the GPW Benchmark website
- **Comprehensive Validation**: Validates share percentages sum to 100% for each index and date combination
- **Reference Datasets**: Pre-generated complete historical datasets in multiple formats

### Core Features
- **Automated PDF Download**: Downloads index composition PDFs from GPW Benchmark website for specific dates
- **Robust PDF Parsing**: Extracts tabular data from complex PDF layouts with space-separated columns
- **ISIN Validation**: Comprehensive validation for both Polish and international ISIN codes
- **Multiple Output Formats**: Exports data to CSV, Excel, SQLite, and JSON formats
- **Data Validation**: Validates extracted data including share percentages and numeric values
- **Polish Market Support**: Handles Polish company names, PLN currency, and Polish ISIN formats

## 📊 Ready-to-Use Datasets

**Complete historical datasets are available in [`datasets/historical/`](datasets/historical/)**

### 🗂️ Reference Files
- **Excel**: [`wse_complete_historical_20250916.xlsx`](datasets/historical/wse_complete_historical_20250916.xlsx) - Multi-sheet Excel with 65+ sheets by date
- **CSV**: [`wse_complete_historical_20250916.csv`](datasets/historical/wse_complete_historical_20250916.csv) - Complete 29,378 records dataset
- **SQLite**: [`wse_complete_historical_20250916.sqlite`](datasets/historical/wse_complete_historical_20250916.sqlite) - Optimized database for analysis  
- **JSON**: [`wse_complete_historical_20250916.json`](datasets/historical/wse_complete_historical_20250916.json) - API integration format

### 📈 Dataset Coverage
- **29,378 total records** extracted from **372 PDFs**
- **83 historical dates** spanning **2004-2024** (20 years)
- **5 indices**: WIG, WIG20, WIG30, mWIG40, sWIG80
- **Data validation**: 236/300 index-date combinations valid (78.7%)
- **Market evolution**: From 267 companies (2007) to 405 peak (2017) to 331 current (2024)

### 🔄 Regenerating Complete Dataset

To regenerate the complete historical dataset with ALL available data:

```bash
# Generate complete dataset (processes ALL 372 PDFs across 83 dates)
python src/generate_historical_dataset.py

# This process will:
# 1. Discover all 372 available PDFs from GPW Benchmark (2004-2024)
# 2. Download PDFs for all 83 historical dates
# 3. Parse and validate all index compositions  
# 4. Create SQLite database with optimized indexes
# 5. Export to Excel (multi-sheet), CSV, and JSON formats
# 6. Generate comprehensive summary and README

# Note: Complete generation takes ~30-45 minutes depending on network speed
# The process downloads ~100MB of PDFs and creates ~3MB of structured data
```

**⚠️ Processing Time**: Complete dataset generation processes all available historical data and may take 30-45 minutes. For quick testing, use:

```bash
# Generate sample dataset (10 recent dates only)
python src/generate_historical_dataset.py --max-dates 10
```

## Installation

### Using uv (recommended)

```bash
git clone https://github.com/skonop/wse-indices-weights-loader.git
cd wse-indices-weights-loader
uv sync
```

### Using pip

```bash
git clone https://github.com/skonop/wse-indices-weights-loader.git
cd wse-indices-weights-loader
pip install -e .
```

## Quick Start

### 🚀 Using Pre-Generated Datasets (Fastest)

```python
import pandas as pd
import sqlite3

# Option 1: Use SQLite database (recommended for analysis)
conn = sqlite3.connect('datasets/historical/wse_complete_historical_20250916.sqlite')

# Get latest WIG20 composition
df = pd.read_sql_query("""
    SELECT * FROM stock_records 
    WHERE index_name = 'WIG20' AND date = (SELECT MAX(date) FROM stock_records)
    ORDER BY share_percent DESC
""", conn)

# Option 2: Use CSV file (universal compatibility)
df = pd.read_csv('datasets/historical/wse_complete_historical_20250916.csv')
latest_wig = df[(df['Index_Name'] == 'WIG') & (df['Date'] == df['Date'].max())]
```

### 🔄 Generate Fresh Data

```bash
# Run quick test with 3 most recent dates
python src/wse_indices_v2.py --test

# Process all available indices and dates (may take time)
python src/wse_indices_v2.py

# Process limited number of recent dates
python src/wse_indices_v2.py --limit-dates 10

# Generate complete historical dataset
python src/generate_historical_dataset.py --max-dates 10
```

### ⚡ Incremental Updates

```bash
# Update dataset with only new PDFs (efficient for regular updates)
python src/incremental_updater.py --reference-db datasets/historical/wse_complete_historical_20250916.sqlite

# The updater automatically:
# - Checks latest date in reference database
# - Downloads only newer PDFs
# - Appends new data to SQLite database  
# - Creates updated export files
# - Reports "up to date" if no new data found
```

### 🔬 Advanced Usage Examples

```python
# Example 1: Analyze market evolution over time
import sqlite3
import pandas as pd

conn = sqlite3.connect('datasets/historical/wse_complete_historical_20250916.sqlite')

# Track WIG index size evolution
evolution = pd.read_sql_query("""
    SELECT date, COUNT(*) as company_count, 
           AVG(share_percent) as avg_weight,
           MAX(share_percent) as max_weight
    FROM stock_records 
    WHERE index_name = 'WIG'
    GROUP BY date 
    ORDER BY date
""", conn)

# Example 2: Find companies present in multiple indices
multi_index = pd.read_sql_query("""
    SELECT company_name, date, GROUP_CONCAT(index_name) as indices,
           COUNT(DISTINCT index_name) as index_count
    FROM stock_records 
    WHERE date = '2024_06_21'
    GROUP BY company_name, date
    HAVING index_count > 1
    ORDER BY index_count DESC
""", conn)

# Example 3: Top weighted companies across all indices
top_weights = pd.read_sql_query("""
    SELECT company_name, index_name, date, share_percent
    FROM stock_records 
    WHERE share_percent > 5.0
    ORDER BY share_percent DESC
""", conn)
```

### v0.1 Basic Usage (Legacy)

```python
from src.pdf_downloader import PDFDownloader
from src.pdf_parser import PDFParser

# Download PDFs for a specific date
downloader = PDFDownloader()
pdf_files = downloader.download_for_date("2024_06_21")

# Parse a specific PDF
parser = PDFParser()
stocks = parser.parse_pdf("wig_2024_06_21.pdf")

# Export to different formats
parser.export_to_csv(stocks, "wig_composition.csv")
parser.export_to_excel(stocks, "wig_composition.xlsx")
parser.export_to_json(stocks, "wig_composition.json")
```

## Data Structure

### v0.2 Multi-Index Output

The v0.2 version creates comprehensive reports:

**Multi-Sheet Excel**: Each sheet represents one date with consolidated view:
- **Base columns**: ISIN, Company_Name
- **Per-index columns**: WIG_No, WIG_Price_PLN, WIG_Number_of_Shares, WIG_Share_Percent, WIG20_No, WIG20_Price_PLN, etc.
- **Validation**: All share percentages validated to sum to ~100% per index

**CSV Export**: Flat structure with index_name and date columns for analysis
**JSON Export**: Complete structured data for API integration
**Summary Report**: Statistics about dates, indices, and companies covered

### v0.1 Individual Record Structure

Each stock record contains:
- **No**: Sequential number in the index
- **ISIN**: International Securities Identification Number
- **Company Name**: Full company name
- **Price (PLN)**: Stock price in Polish Złoty
- **Number of Shares**: Total shares in the index
- **Share Percentage**: Weight percentage in the index
- **Index Name**: Name of the index (v0.2)
- **Date**: Date of the composition (v0.2)

Example output:
```json
{
  "no": 1,
  "isin": "PLPKO0000016",
  "company_name": "PKO BP",
  "price_pln": 45.86,
  "number_of_shares": 12500000,
  "share_percent": 14.2345,
  "index_name": "WIG",
  "date": "2024_06_21"
}
```

## Supported Indices

v0.2 automatically discovers and processes all available indices:
- **WIG**: Main index of the Warsaw Stock Exchange (~330 companies)
- **WIG20**: Large-cap index (20 largest companies)
- **WIG30**: Extended large-cap index (30 companies)  
- **mWIG40**: Medium-sized companies index (40 companies)
- **sWIG80**: Small-sized companies index (80 companies)
- Other historical indices as discovered from GPW Benchmark

The tool automatically identifies available indices for each date and downloads all found PDFs.

## ISIN Validation

The tool includes comprehensive ISIN validation:
- **Polish ISINs**: PL + alphanumeric company identifier (supporting cases like 11BIT)
- **International ISINs**: Standard 2-letter country code + 10 alphanumeric characters
- **Format validation**: Ensures proper length, character types, and check digit placement

## Development
```bash
### Setting up Development Environment

```bash
# Clone the repository
git clone https://github.com/skonop/wse-indices-weights-loader.git
cd wse-indices-weights-loader

# Install dependencies
uv sync

# Run tests
uv run python -m pytest tests/

# Run the main application
uv run python src/__main__.py
```

### Project Structure

```
.
├── src/                    # Source code
│   ├── __init__.py
│   ├── __main__.py        # Entry point
│   ├── pdf_downloader.py  # PDF download functionality
│   └── pdf_parser.py      # PDF parsing logic
├── tests/                  # Test files
├── Makefile               # Development commands
├── pyproject.toml         # Project configuration
└── README.md              # This file
```

## API Documentation

### PDFDownloader

Downloads PDF files from GPW Benchmark website.

```python
from src.pdf_downloader import PDFDownloader

downloader = PDFDownloader()

# Download all available PDFs for a specific date
pdf_files = downloader.download_for_date("2024_06_21")

# Download specific index for a date
pdf_file = downloader.download_pdf("wig", "2024_06_21")
```

### PDFParser

Parses downloaded PDF files and extracts stock data.

```python
from src.pdf_parser import PDFParser

parser = PDFParser()

# Parse a PDF file
stocks = parser.parse_pdf("wig_2024_06_21.pdf")

# Export to different formats
parser.export_to_csv(stocks, "output.csv")
parser.export_to_excel(stocks, "output.xlsx")
parser.export_to_json(stocks, "output.json")
```

### StockRecord

Data structure representing a single stock entry:

```python
@dataclass
class StockRecord:
    no: int                    # Sequential number
    isin: str                  # ISIN code
    company_name: str          # Company name
    price_pln: float          # Price in PLN
    number_of_shares: int     # Number of shares
    share_percent: float      # Percentage weight in index
    index_name: str           # Index name (v0.2)
    date: str                 # Date (v0.2)
```

## v0.2 Example Output

After running the quick test, you'll get:

```
✅ WSE Indices v0.2 processing completed successfully!
📊 Generated files:
   - wse_test_v2_20250916_102832.xlsx (Multi-sheet Excel)
   - wse_test_v2_20250916_102832.csv (Complete dataset)
   - wse_test_v2_20250916_102832.json (API-ready data)
   - wse_test_summary_20250916_102832.txt (Statistics)

📈 Statistics:
   - Total Records: 1,500
   - Unique Companies: 344
   - Indices Covered: 5 (WIG, WIG20, WIG30, mWIG40, sWIG80)
   - Dates Processed: 3
   - Validation: 15/15 index-date combinations valid (100%)
```

## Error Handling

The tool includes comprehensive error handling for:
- Network connectivity issues
- Invalid PDF formats
- Parsing errors
- File I/O errors
- Data validation failures

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## Acknowledgments

This project was developed with significant assistance from AI (GitHub Copilot/Claude), which helped with:
- Code implementation and architecture design
- PDF parsing algorithm development
- Test suite creation and debugging
- Documentation and project structure
- Polish market-specific requirements handling

The AI assistance enabled rapid prototyping and comprehensive testing while maintaining code quality and best practices.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Changelog

### v0.2.0 (Current)
- **Multi-Index Support**: Process all 5 indices (WIG, WIG20, WIG30, mWIG40, sWIG80) simultaneously
- **Complete Historical Dataset**: Generated comprehensive dataset with 29,378 records from 372 PDFs (2004-2024)
- **Advanced Data Discovery**: Automatic discovery of all available PDFs from GPW Benchmark website
- **Multi-Format Export**: SQLite database, multi-sheet Excel, CSV, and JSON formats
- **Incremental Updates**: Efficient system to update datasets with only new data
- **Comprehensive Validation**: Share percentage validation and data quality checks
- **Ready-to-Use Reference Datasets**: Pre-generated complete historical datasets in repository

### v0.1.0 
- Initial release with basic single-index processing
- PDF download functionality  
- PDF parsing with ISIN validation
- Support for Polish and international ISINs
- Multiple export formats (CSV, Excel, JSON)
- Comprehensive test suite
