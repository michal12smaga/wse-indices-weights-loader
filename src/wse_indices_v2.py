#!/usr/bin/env python3
"""
WSE Indices Weights Loader v0.2 - Multi-Index Support
Download and parse multiple index PDFs to create consolidated Excel reports.
"""

import os
import sys
from typing import Dict, List, Tuple
from datetime import datetime
import argparse

from pdf_downloader import PDFDownloader
from pdf_parser import PDFParser, StockRecord


class WSEIndicesLoaderV2:
    """Main application for WSE indices data loading with multi-index support."""

    def __init__(self, output_dir: str = "data"):
        self.downloader = PDFDownloader(output_dir)
        self.parser = PDFParser()
        self.output_dir = output_dir

    def load_all_indices_for_dates(self, limit_dates: int = None) -> List[StockRecord]:
        """
        Download and parse all available indices for all dates.

        Args:
            limit_dates: Optional limit on number of dates to process (for testing)

        Returns:
            List of all stock records across all indices and dates
        """
        print("=" * 60)
        print("WSE Indices Weights Loader v0.2 - Multi-Index Support")
        print("=" * 60)

        # Step 1: Discover all available PDFs
        print("\n1. Discovering all available PDFs...")
        all_pdfs = self.downloader.discover_all_pdfs()

        if not all_pdfs:
            print("❌ No PDFs discovered. Check network connection.")
            return []

        dates = sorted(all_pdfs.keys())
        if limit_dates:
            dates = dates[-limit_dates:]  # Take most recent dates
            print(f"   Limited to {limit_dates} most recent dates")

        print(f"   Found PDFs for {len(dates)} dates")
        print(f"   Date range: {dates[0]} to {dates[-1]}")

        # Step 2: Download PDFs for selected dates
        print(f"\n2. Downloading PDFs for {len(dates)} dates...")
        downloaded_files = []

        for i, date in enumerate(dates, 1):
            print(f"   Processing date {i}/{len(dates)}: {date}")
            date_urls = all_pdfs[date]

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
            print("❌ No files downloaded successfully.")
            return []

        print(f"   Successfully downloaded {len(downloaded_files)} files")

        # Step 3: Parse all downloaded PDFs
        print(f"\n3. Parsing {len(downloaded_files)} PDF files...")
        all_records = self.parser.parse_multiple_pdfs(downloaded_files)

        if not all_records:
            print("❌ No records extracted from PDFs.")
            return []

        print(f"   Extracted {len(all_records)} total records")

        # Step 4: Validate data quality
        print("\n4. Validating data quality...")
        validation_results = self.parser.validate_share_percentages_by_index(
            all_records)

        valid_count = sum(1 for result in validation_results.values()
                          if result['validation']['valid'])
        total_count = len(validation_results)

        print(
            f"   Validation: {valid_count}/{total_count} index-date combinations are valid")

        # Show any validation issues
        for key, result in validation_results.items():
            validation = result['validation']
            if not validation['valid']:
                issues = []
                if not validation['share_percent_valid']:
                    issues.append(
                        f"shares sum to {validation['total_share_percent']:.2f}%")
                if validation['has_duplicates']:
                    issues.append("has duplicates")
                if validation['has_missing_data']:
                    issues.append("has missing data")
                print(
                    f"     ⚠️  {result['index_name']} on {result['date']}: {', '.join(issues)}")

        return all_records

    def create_reports(self, records: List[StockRecord], base_filename: str = "wse_indices_report"):
        """Create various output reports from the extracted data."""
        if not records:
            print("No records to create reports from.")
            return

        print(f"\n5. Creating reports...")

        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 1. Multi-sheet Excel (main deliverable for v0.2)
        excel_path = os.path.join(
            self.output_dir, f"{base_filename}_v2_{timestamp}.xlsx")
        self.parser.export_to_multi_sheet_excel(records, excel_path)
        print(f"   ✓ Multi-sheet Excel: {excel_path}")

        # 2. CSV for data analysis
        csv_path = os.path.join(
            self.output_dir, f"{base_filename}_v2_{timestamp}.csv")
        self.parser.export_to_csv(records, csv_path)
        print(f"   ✓ CSV export: {csv_path}")

        # 3. JSON for API usage
        json_path = os.path.join(
            self.output_dir, f"{base_filename}_v2_{timestamp}.json")
        self.parser.export_to_json(records, json_path)
        print(f"   ✓ JSON export: {json_path}")

        # 4. Summary statistics
        self._create_summary_report(records, base_filename, timestamp)

        print(f"\n✅ Complete! All reports saved to {self.output_dir}/")

    def _create_summary_report(self, records: List[StockRecord], base_filename: str, timestamp: str):
        """Create a summary report with statistics."""
        summary_path = os.path.join(
            self.output_dir, f"{base_filename}_summary_{timestamp}.txt")

        # Gather statistics
        dates = set(record.date for record in records)
        indices = set(record.index_name for record in records)
        companies = set(record.isin for record in records)

        # Group by index and date for more detailed stats
        by_index = {}
        by_date = {}

        for record in records:
            if record.index_name not in by_index:
                by_index[record.index_name] = []
            by_index[record.index_name].append(record)

            if record.date not in by_date:
                by_date[record.date] = []
            by_date[record.date].append(record)

        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("WSE Indices Weights Loader v0.2 - Summary Report\n")
            f.write("=" * 55 + "\n\n")

            f.write(
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Records: {len(records)}\n")
            f.write(f"Unique Companies: {len(companies)}\n")
            f.write(f"Indices Covered: {len(indices)}\n")
            f.write(f"Dates Covered: {len(dates)}\n\n")

            f.write("Indices:\n")
            for index_name in sorted(indices):
                count = len(by_index[index_name])
                f.write(f"  {index_name}: {count} records\n")

            f.write(f"\nDates (showing first 10 and last 10):\n")
            sorted_dates = sorted(dates)
            if len(sorted_dates) <= 20:
                for date in sorted_dates:
                    count = len(by_date[date])
                    f.write(f"  {date}: {count} records\n")
            else:
                for date in sorted_dates[:10]:
                    count = len(by_date[date])
                    f.write(f"  {date}: {count} records\n")
                f.write(
                    f"  ... ({len(sorted_dates) - 20} dates omitted) ...\n")
                for date in sorted_dates[-10:]:
                    count = len(by_date[date])
                    f.write(f"  {date}: {count} records\n")

        print(f"   ✓ Summary report: {summary_path}")

    def quick_test(self, num_dates: int = 3) -> bool:
        """
        Quick test with limited data for development/testing.

        Args:
            num_dates: Number of recent dates to test with

        Returns:
            True if test successful, False otherwise
        """
        print(f"🧪 Running quick test with {num_dates} most recent dates...")

        records = self.load_all_indices_for_dates(limit_dates=num_dates)

        if records:
            self.create_reports(records, "wse_test")
            print("✅ Quick test completed successfully!")
            return True
        else:
            print("❌ Quick test failed - no data extracted")
            return False


def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(
        description="WSE Indices Weights Loader v0.2 - Multi-Index Support"
    )

    parser.add_argument(
        "--output-dir", "-o",
        default="data",
        help="Output directory for downloaded files and reports (default: data)"
    )

    parser.add_argument(
        "--test", "-t",
        action="store_true",
        help="Run quick test with 3 most recent dates"
    )

    parser.add_argument(
        "--limit-dates", "-l",
        type=int,
        help="Limit processing to N most recent dates (for testing)"
    )

    args = parser.parse_args()

    # Create the loader
    loader = WSEIndicesLoaderV2(output_dir=args.output_dir)

    try:
        if args.test:
            # Quick test mode
            success = loader.quick_test()
            sys.exit(0 if success else 1)
        else:
            # Full processing
            records = loader.load_all_indices_for_dates(
                limit_dates=args.limit_dates)
            if records:
                loader.create_reports(records)
                print("\n🎉 WSE Indices v0.2 processing completed successfully!")
            else:
                print("\n❌ Processing failed - no data extracted")
                sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⏹️  Processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
