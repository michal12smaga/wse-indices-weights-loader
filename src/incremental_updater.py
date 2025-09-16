#!/usr/bin/env python3
"""
Incremental Update System for WSE Indices
Only processes PDFs newer than the latest date in existing dataset.
"""

import os
import sys
import sqlite3
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional, Tuple

from pdf_parser import PDFParser, StockRecord
from wse_indices_v2 import WSEIndicesLoaderV2


class IncrementalUpdater(WSEIndicesLoaderV2):
    """Incremental updater that only processes new PDFs."""

    def __init__(self, reference_db_path: str, output_dir: str = "datasets/historical"):
        super().__init__(output_dir)
        self.reference_db_path = reference_db_path
        self.latest_date_in_db = None

    def get_latest_date_from_database(self) -> Optional[str]:
        """Get the latest date from the reference database."""
        if not os.path.exists(self.reference_db_path):
            print(f"Reference database not found: {self.reference_db_path}")
            return None

        try:
            conn = sqlite3.connect(self.reference_db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(date) FROM stock_records")
            result = cursor.fetchone()
            conn.close()

            if result and result[0]:
                self.latest_date_in_db = result[0]
                print(
                    f"Latest date in reference database: {self.latest_date_in_db}")
                return result[0]
            else:
                print("No data found in reference database")
                return None
        except Exception as e:
            print(f"Error reading reference database: {e}")
            return None

    def discover_new_pdfs_only(self) -> Dict[str, List[str]]:
        """Discover only PDFs newer than the latest date in database."""
        print("🔍 Discovering new PDFs since last update...")

        # Get all available PDFs
        all_pdfs = self.downloader.discover_all_pdfs()

        if not all_pdfs:
            print("❌ No PDFs discovered from website")
            return {}

        # Get latest date from database
        latest_db_date = self.get_latest_date_from_database()

        if not latest_db_date:
            print("📋 No reference database found - will process all available PDFs")
            return all_pdfs

        # Filter for dates newer than latest in database
        new_pdfs = {}
        for date_str, pdf_urls in all_pdfs.items():
            if date_str > latest_db_date:  # String comparison works for YYYY_MM_DD format
                new_pdfs[date_str] = pdf_urls

        if new_pdfs:
            dates = sorted(new_pdfs.keys())
            print(
                f"✨ Found {len(new_pdfs)} new dates: {dates[0]} to {dates[-1]}")
            total_files = sum(len(urls) for urls in new_pdfs.values())
            print(f"📄 Total new PDFs to process: {total_files}")
        else:
            print("✅ No new PDFs found - database is up to date!")

        return new_pdfs

    def update_incremental_dataset(self) -> bool:
        """
        Perform incremental update of the dataset.

        Returns:
            True if update successful or no updates needed, False if failed
        """
        print("=" * 70)
        print("WSE Indices Incremental Update System")
        print("=" * 70)

        # Discover only new PDFs
        new_pdfs = self.discover_new_pdfs_only()

        if not new_pdfs:
            print("\n✅ Dataset is already up to date!")
            return True

        # Process new PDFs using the same logic as full loader
        new_records = self._process_new_pdfs(new_pdfs)

        if not new_records:
            print("❌ No new records extracted")
            return False

        # Update the reference database and create updated exports
        success = self._update_datasets(new_records)

        if success:
            print(f"\n🎉 Incremental update completed successfully!")
            print(f"📊 Added {len(new_records)} new records")
            return True
        else:
            print(f"\n❌ Incremental update failed")
            return False

    def _process_new_pdfs(self, new_pdfs: Dict[str, List[str]]) -> List[StockRecord]:
        """Process the newly discovered PDFs."""
        dates = sorted(new_pdfs.keys())

        print(f"\n2. Downloading and parsing {len(dates)} new dates...")
        downloaded_files = []

        for i, date in enumerate(dates, 1):
            print(f"   Processing new date {i}/{len(dates)}: {date}")
            date_urls = new_pdfs[date]

            for pdf_url in date_urls:
                # Extract index name from URL for display
                filename = os.path.basename(pdf_url)
                index_name = filename.replace(
                    f"{date}_", "").replace(".pdf", "")

                file_path = self.downloader.download_pdf(pdf_url)
                if file_path:
                    downloaded_files.append(file_path)
                    print(f"     ✓ {index_name}")
                else:
                    print(f"     ✗ {index_name} (download failed)")

        if not downloaded_files:
            print("❌ No new files downloaded successfully.")
            return []

        print(f"   Successfully downloaded {len(downloaded_files)} new files")

        # Parse all new PDFs
        print(f"\n3. Parsing {len(downloaded_files)} new PDF files...")
        new_records = self.parser.parse_multiple_pdfs(downloaded_files)

        if not new_records:
            print("❌ No records extracted from new PDFs.")
            return []

        print(f"   Extracted {len(new_records)} new records")

        # Validate new data
        print("\n4. Validating new data quality...")
        validation_results = self.parser.validate_share_percentages_by_index(
            new_records)

        valid_count = sum(1 for result in validation_results.values()
                          if result['validation']['valid'])
        total_count = len(validation_results)

        print(
            f"   Validation: {valid_count}/{total_count} new index-date combinations are valid")

        return new_records

    def _update_datasets(self, new_records: List[StockRecord]) -> bool:
        """Update the reference database and create new exports."""
        try:
            print(f"\n5. Updating reference database...")

            # Add new records to the reference database
            self._append_to_sqlite_database(new_records)
            print(f"   ✓ Added {len(new_records)} records to SQLite database")

            # Create updated exports
            timestamp = datetime.now().strftime("%Y%m%d")
            base_filename = f"wse_complete_historical_{timestamp}"

            # Export all data (existing + new) to new files
            all_records = self._load_all_records_from_database()
            self._create_updated_exports(all_records, base_filename)

            return True

        except Exception as e:
            print(f"   ❌ Error updating datasets: {e}")
            return False

    def _append_to_sqlite_database(self, new_records: List[StockRecord]):
        """Append new records to the existing SQLite database."""
        conn = sqlite3.connect(self.reference_db_path)
        cursor = conn.cursor()

        # Insert new data in batches
        batch_size = 1000
        data_to_insert = [
            (record.date, record.index_name, record.no, record.isin,
             record.company_name, record.price_pln, record.number_of_shares,
             record.share_percent)
            for record in new_records
        ]

        for i in range(0, len(data_to_insert), batch_size):
            batch = data_to_insert[i:i + batch_size]
            cursor.executemany('''
                INSERT INTO stock_records 
                (date, index_name, no, isin, company_name, price_pln, number_of_shares, share_percent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', batch)

        # Update summary tables
        cursor.execute('DROP TABLE IF EXISTS summary_by_date')
        cursor.execute('DROP TABLE IF EXISTS summary_by_index')

        cursor.execute('''
            CREATE TABLE summary_by_date AS
            SELECT 
                date,
                COUNT(*) as total_records,
                COUNT(DISTINCT index_name) as indices_count,
                COUNT(DISTINCT isin) as unique_companies
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

    def _load_all_records_from_database(self) -> List[StockRecord]:
        """Load all records from the updated database."""
        conn = sqlite3.connect(self.reference_db_path)

        query = """
            SELECT date, index_name, no, isin, company_name, 
                   price_pln, number_of_shares, share_percent
            FROM stock_records 
            ORDER BY date, index_name, no
        """

        df = pd.read_sql_query(query, conn)
        conn.close()

        records = []
        for _, row in df.iterrows():
            record = StockRecord(
                no=row['no'],
                isin=row['isin'],
                company_name=row['company_name'],
                price_pln=row['price_pln'],
                number_of_shares=row['number_of_shares'],
                share_percent=row['share_percent'],
                index_name=row['index_name'],
                date=row['date']
            )
            records.append(record)

        return records

    def _create_updated_exports(self, all_records: List[StockRecord], base_filename: str):
        """Create updated export files with all data."""
        print(f"   📊 Creating updated exports...")

        # Excel export
        excel_path = os.path.join(self.output_dir, f"{base_filename}.xlsx")
        self.parser.export_to_multi_sheet_excel(all_records, excel_path)
        print(f"   ✓ Updated Excel: {excel_path}")

        # CSV export
        csv_path = os.path.join(self.output_dir, f"{base_filename}.csv")
        self.parser.export_to_csv(all_records, csv_path)
        print(f"   ✓ Updated CSV: {csv_path}")

        # JSON export
        json_path = os.path.join(self.output_dir, f"{base_filename}.json")
        self.parser.export_to_json(all_records, json_path)
        print(f"   ✓ Updated JSON: {json_path}")


def main():
    """Main entry point for incremental updates."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Incremental update of WSE indices dataset"
    )

    parser.add_argument(
        "--reference-db",
        required=True,
        help="Path to reference SQLite database"
    )

    parser.add_argument(
        "--output-dir", "-o",
        default="datasets/historical",
        help="Output directory (default: datasets/historical)"
    )

    args = parser.parse_args()

    if not os.path.exists(args.reference_db):
        print(f"❌ Reference database not found: {args.reference_db}")
        sys.exit(1)

    updater = IncrementalUpdater(
        reference_db_path=args.reference_db,
        output_dir=args.output_dir
    )

    try:
        success = updater.update_incremental_dataset()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Update interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during incremental update: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
