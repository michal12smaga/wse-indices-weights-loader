#!/usr/bin/env python3
"""
WSE Indices Complete Historical Dataset Generator
Creates comprehensive reference datasets including SQLite database.
"""

import os
import sys
import sqlite3
import pandas as pd
from datetime import datetime
from typing import List, Dict

from pdf_parser import PDFParser, StockRecord
from wse_indices_v2 import WSEIndicesLoaderV2


class HistoricalDatasetGenerator(WSEIndicesLoaderV2):
    """Enhanced loader for creating comprehensive historical datasets."""

    def __init__(self, output_dir: str = "datasets/historical"):
        super().__init__(output_dir)
        self.db_path = None

    def create_complete_historical_dataset(self, max_dates: int = None) -> bool:
        """
        Create complete historical dataset with all available data.

        Args:
            max_dates: Optional limit for testing (None = all available dates)

        Returns:
            True if successful, False otherwise
        """
        print("=" * 70)
        print("WSE Indices Complete Historical Dataset Generator")
        print("=" * 70)

        # Generate all records
        records = self.load_all_indices_for_dates(limit_dates=max_dates)

        if not records:
            print("❌ No data to export")
            return False

        # Create comprehensive reports including SQLite
        timestamp = datetime.now().strftime("%Y%m%d")
        base_filename = f"wse_complete_historical_{timestamp}"

        success = self.create_comprehensive_reports(records, base_filename)

        if success:
            self._create_dataset_readme(records, timestamp)
            print(f"\n🎉 Complete historical dataset created successfully!")
            print(f"📁 Location: {self.output_dir}/")
            return True
        else:
            print(f"\n❌ Failed to create complete historical dataset")
            return False

    def create_comprehensive_reports(self, records: List[StockRecord], base_filename: str):
        """Create comprehensive reports including SQLite database."""
        if not records:
            print("No records to create reports from.")
            return False

        print(f"\n5. Creating comprehensive historical reports...")

        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)

        try:
            # 1. SQLite Database (most efficient for large datasets)
            sqlite_path = os.path.join(
                self.output_dir, f"{base_filename}.sqlite")
            self._create_sqlite_database(records, sqlite_path)
            print(f"   ✓ SQLite database: {sqlite_path}")

            # 2. Multi-sheet Excel (main deliverable)
            excel_path = os.path.join(self.output_dir, f"{base_filename}.xlsx")
            self.parser.export_to_multi_sheet_excel(records, excel_path)
            print(f"   ✓ Multi-sheet Excel: {excel_path}")

            # 3. Complete CSV (for analysis)
            csv_path = os.path.join(self.output_dir, f"{base_filename}.csv")
            self.parser.export_to_csv(records, csv_path)
            print(f"   ✓ Complete CSV: {csv_path}")

            # 4. Compressed JSON (for API usage)
            json_path = os.path.join(self.output_dir, f"{base_filename}.json")
            self.parser.export_to_json(records, json_path)
            print(f"   ✓ JSON export: {json_path}")

            # 5. Summary statistics
            self._create_comprehensive_summary(records, base_filename)

            return True

        except Exception as e:
            print(f"   ❌ Error creating reports: {e}")
            return False

    def _create_sqlite_database(self, records: List[StockRecord], db_path: str):
        """Create SQLite database with optimized schema."""
        # Remove existing database
        if os.path.exists(db_path):
            os.remove(db_path)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Create optimized table with indexes
        cursor.execute('''
            CREATE TABLE stock_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                index_name TEXT NOT NULL,
                no INTEGER NOT NULL,
                isin TEXT NOT NULL,
                company_name TEXT NOT NULL,
                price_pln REAL NOT NULL,
                number_of_shares INTEGER NOT NULL,
                share_percent REAL NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create indexes for efficient querying
        cursor.execute('CREATE INDEX idx_date ON stock_records(date)')
        cursor.execute(
            'CREATE INDEX idx_index_name ON stock_records(index_name)')
        cursor.execute('CREATE INDEX idx_isin ON stock_records(isin)')
        cursor.execute(
            'CREATE INDEX idx_date_index ON stock_records(date, index_name)')

        # Insert data in batches for efficiency
        batch_size = 1000
        data_to_insert = [
            (record.date, record.index_name, record.no, record.isin,
             record.company_name, record.price_pln, record.number_of_shares,
             record.share_percent)
            for record in records
        ]

        for i in range(0, len(data_to_insert), batch_size):
            batch = data_to_insert[i:i + batch_size]
            cursor.executemany('''
                INSERT INTO stock_records 
                (date, index_name, no, isin, company_name, price_pln, number_of_shares, share_percent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', batch)

        # Create summary tables for quick access
        cursor.execute('''
            CREATE TABLE summary_by_date AS
            SELECT 
                date,
                COUNT(*) as total_records,
                COUNT(DISTINCT index_name) as indices_count,
                COUNT(DISTINCT isin) as unique_companies,
                MIN(index_name) as indices_list
            FROM stock_records 
            GROUP BY date
            ORDER BY date
        ''')

        cursor.execute('''
            CREATE TABLE summary_by_index AS
            SELECT 
                index_name,
                COUNT(*) as total_records,
                COUNT(DISTINCT date) as dates_count,
                COUNT(DISTINCT isin) as unique_companies,
                MIN(date) as earliest_date,
                MAX(date) as latest_date
            FROM stock_records 
            GROUP BY index_name
            ORDER BY index_name
        ''')

        conn.commit()
        conn.close()

        self.db_path = db_path

    def _create_comprehensive_summary(self, records: List[StockRecord], base_filename: str):
        """Create detailed summary with statistics and metadata."""
        summary_path = os.path.join(
            self.output_dir, f"{base_filename}_summary.txt")

        # Gather comprehensive statistics
        dates = sorted(set(record.date for record in records))
        indices = sorted(set(record.index_name for record in records))
        companies = set(record.isin for record in records)

        # Detailed stats by index and date
        by_index = {}
        by_date = {}
        by_index_date = {}

        for record in records:
            # By index
            if record.index_name not in by_index:
                by_index[record.index_name] = []
            by_index[record.index_name].append(record)

            # By date
            if record.date not in by_date:
                by_date[record.date] = []
            by_date[record.date].append(record)

            # By index-date combination
            key = f"{record.index_name}_{record.date}"
            if key not in by_index_date:
                by_index_date[key] = []
            by_index_date[key].append(record)

        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("WSE Indices Complete Historical Dataset - Summary\n")
            f.write("=" * 55 + "\n\n")

            f.write(
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(
                f"Dataset Version: {datetime.now().strftime('%Y%m%d')}\n\n")

            f.write("OVERVIEW\n")
            f.write("-" * 20 + "\n")
            f.write(f"Total Records: {len(records):,}\n")
            f.write(f"Unique Companies (ISINs): {len(companies):,}\n")
            f.write(f"Indices Covered: {len(indices)}\n")
            f.write(f"Dates Covered: {len(dates)}\n")
            f.write(f"Date Range: {dates[0]} to {dates[-1]}\n\n")

            f.write("INDICES COVERAGE\n")
            f.write("-" * 20 + "\n")
            for index_name in indices:
                records_count = len(by_index[index_name])
                dates_count = len(set(r.date for r in by_index[index_name]))
                companies_count = len(
                    set(r.isin for r in by_index[index_name]))
                f.write(f"{index_name}:\n")
                f.write(f"  Records: {records_count:,}\n")
                f.write(f"  Dates: {dates_count}\n")
                f.write(f"  Companies: {companies_count}\n\n")

            f.write("TEMPORAL COVERAGE\n")
            f.write("-" * 20 + "\n")
            f.write(f"First Date: {dates[0]}\n")
            f.write(f"Latest Date: {dates[-1]}\n")
            f.write(f"Total Trading Days: {len(dates)}\n\n")

            if len(dates) <= 20:
                f.write("All Dates:\n")
                for date in dates:
                    count = len(by_date[date])
                    indices_count = len(
                        set(r.index_name for r in by_date[date]))
                    f.write(
                        f"  {date}: {count:,} records ({indices_count} indices)\n")
            else:
                f.write("First 10 Dates:\n")
                for date in dates[:10]:
                    count = len(by_date[date])
                    indices_count = len(
                        set(r.index_name for r in by_date[date]))
                    f.write(
                        f"  {date}: {count:,} records ({indices_count} indices)\n")
                f.write(f"\n  ... ({len(dates) - 20} dates omitted) ...\n\n")
                f.write("Last 10 Dates:\n")
                for date in dates[-10:]:
                    count = len(by_date[date])
                    indices_count = len(
                        set(r.index_name for r in by_date[date]))
                    f.write(
                        f"  {date}: {count:,} records ({indices_count} indices)\n")

            f.write(f"\nFILE FORMATS\n")
            f.write("-" * 20 + "\n")
            f.write(
                f"SQLite Database: {base_filename}.sqlite (recommended for analysis)\n")
            f.write(
                f"Excel Multi-sheet: {base_filename}.xlsx (human-readable)\n")
            f.write(
                f"CSV Complete: {base_filename}.csv (universal compatibility)\n")
            f.write(f"JSON Complete: {base_filename}.json (API integration)\n")

        print(f"   ✓ Comprehensive summary: {summary_path}")

    def _create_dataset_readme(self, records: List[StockRecord], timestamp: str):
        """Create README file for the dataset."""
        readme_path = os.path.join(self.output_dir, "README.md")

        dates = sorted(set(record.date for record in records))
        indices = sorted(set(record.index_name for record in records))

        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write("# WSE Indices Historical Dataset\n\n")
            f.write(
                "Complete historical dataset of Warsaw Stock Exchange indices composition.\n\n")

            f.write("## Dataset Overview\n\n")
            f.write(
                f"- **Generated**: {datetime.now().strftime('%Y-%m-%d')}\n")
            f.write(f"- **Records**: {len(records):,}\n")
            f.write(f"- **Date Range**: {dates[0]} to {dates[-1]}\n")
            f.write(f"- **Indices**: {', '.join(indices)}\n")
            f.write(
                f"- **Companies**: {len(set(record.isin for record in records))}\n\n")

            f.write("## Files\n\n")
            f.write(f"### Current Dataset ({timestamp})\n\n")
            f.write(
                f"- **`wse_complete_historical_{timestamp}.sqlite`** - SQLite database (recommended)\n")
            f.write(
                f"- **`wse_complete_historical_{timestamp}.xlsx`** - Multi-sheet Excel file\n")
            f.write(
                f"- **`wse_complete_historical_{timestamp}.csv`** - Complete CSV export\n")
            f.write(
                f"- **`wse_complete_historical_{timestamp}.json`** - JSON format\n")
            f.write(
                f"- **`wse_complete_historical_{timestamp}_summary.txt`** - Detailed statistics\n\n")

            f.write("## Usage Examples\n\n")
            f.write("### SQLite Database\n\n")
            f.write("```python\n")
            f.write("import sqlite3\n")
            f.write("import pandas as pd\n\n")
            f.write(f"# Connect to database\n")
            f.write(
                f"conn = sqlite3.connect('wse_complete_historical_{timestamp}.sqlite')\n\n")
            f.write("# Get all WIG records for 2024\n")
            f.write("df = pd.read_sql_query(\"\"\"\n")
            f.write("    SELECT * FROM stock_records \n")
            f.write("    WHERE index_name = 'WIG' AND date LIKE '2024%'\n")
            f.write("    ORDER BY date, share_percent DESC\n")
            f.write("\"\"\", conn)\n\n")
            f.write("# Get summary statistics\n")
            f.write(
                "summary = pd.read_sql_query(\"SELECT * FROM summary_by_index\", conn)\n")
            f.write("print(summary)\n")
            f.write("```\n\n")

            f.write("### Pandas CSV\n\n")
            f.write("```python\n")
            f.write("import pandas as pd\n\n")
            f.write(f"# Load complete dataset\n")
            f.write(
                f"df = pd.read_csv('wse_complete_historical_{timestamp}.csv')\n\n")
            f.write("# Filter for specific index and date\n")
            f.write(
                "wig20_latest = df[(df['Index_Name'] == 'WIG20') & (df['Date'] == df['Date'].max())]\n")
            f.write("```\n\n")

            f.write("## Data Schema\n\n")
            f.write("Each record contains:\n\n")
            f.write("- **date**: Date in YYYY_MM_DD format\n")
            f.write(
                "- **index_name**: Index identifier (WIG, WIG20, WIG30, mWIG40, sWIG80)\n")
            f.write("- **no**: Sequential number in the index\n")
            f.write("- **isin**: International Securities Identification Number\n")
            f.write("- **company_name**: Company name\n")
            f.write("- **price_pln**: Stock price in Polish Złoty\n")
            f.write("- **number_of_shares**: Number of shares in the index\n")
            f.write("- **share_percent**: Weight percentage in the index\n")

        print(f"   ✓ Dataset README: {readme_path}")


def main():
    """Main entry point for historical dataset generation."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate complete WSE indices historical dataset"
    )

    parser.add_argument(
        "--max-dates", "-m",
        type=int,
        help="Maximum number of dates to process (for testing)"
    )

    parser.add_argument(
        "--output-dir", "-o",
        default="datasets/historical",
        help="Output directory (default: datasets/historical)"
    )

    args = parser.parse_args()

    generator = HistoricalDatasetGenerator(output_dir=args.output_dir)

    try:
        success = generator.create_complete_historical_dataset(
            max_dates=args.max_dates)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Dataset generation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error generating dataset: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
