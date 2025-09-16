# WSE Indices Weights Loader

A Python tool for downloading and parsing PDF files containing stock index composition data from the Warsaw Stock Exchange (WSE) via the GPW Benchmark website. This tool extracts structured data about stocks, their weights, prices, and shares from index composition PDFs.

## Features

- **Automated PDF Download**: Downloads index composition PDFs from GPW Benchmark website for specific dates
- **Robust PDF Parsing**: Extracts tabular data from complex PDF layouts with space-separated columns
- **ISIN Validation**: Comprehensive validation for both Polish and international ISIN codes
- **Multiple Output Formats**: Exports data to CSV, Excel, and JSON formats
- **Data Validation**: Validates extracted data including share percentages and numeric values
- **Polish Market Support**: Handles Polish company names, PLN currency, and Polish ISIN formats

## Installation

### Using uv (recommended)

```bash
git clone <repository-url>
cd wse-indices-weights-loader
uv sync
```

### Using pip

```bash
git clone <repository-url>
cd wse-indices-weights-loader
pip install -e .
```

## Quick Start

### Basic Usage

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

### Command Line Usage

```bash
# Run the main script
uv run python src/__main__.py

# Or using the module
uv run python -m src
```

## Data Structure

Each stock record contains:
- **No**: Sequential number in the index
- **ISIN**: International Securities Identification Number
- **Company Name**: Full company name
- **Price (PLN)**: Stock price in Polish Złoty
- **Number of Shares**: Total shares in the index
- **Share Percentage**: Weight percentage in the index

Example output:
```json
{
  "no": 1,
  "isin": "PLPKO0000016",
  "company_name": "PKO BP",
  "price_pln": 45.86,
  "number_of_shares": 12500000,
  "share_percent": 14.2345
}
```

## Supported Indices

- **WIG**: Main index of the Warsaw Stock Exchange
- **mWIG40**: Medium-sized companies index
- **sWIG80**: Small-sized companies index
- Other GPW Benchmark indices

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
git clone <repository-url>
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

### v0.1.0 (Current)
- Initial release
- PDF download functionality
- PDF parsing with ISIN validation
- Support for Polish and international ISINs
- Multiple export formats (CSV, Excel, JSON)
- Comprehensive test suite
