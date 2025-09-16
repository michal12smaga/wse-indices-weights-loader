"""
Main entry point for WSE indices weights loader.
Downloads and parses PDF files containing stock index data from GPW Benchmark.
"""

import os
import sys
import argparse

from .pdf_downloader import PDFDownloader
from .pdf_parser import PDFParser


def main():
    """Main function to orchestrate PDF downloading and parsing."""
    parser = argparse.ArgumentParser(
        description='Download and parse WSE indices weights from PDF files'
    )
    parser.add_argument(
        '--date',
        type=str,
        default='2024_06_21',
        help='Date in format YYYY_MM_DD (default: 2024_06_21)'
    )
    parser.add_argument(
        '--index',
        type=str,
        help='Specific index name (e.g., WIG, WIG20). If not specified, downloads all available.'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='output',
        help='Directory to save output files (default: output)'
    )
    parser.add_argument(
        '--download-dir',
        type=str,
        default='downloads',
        help='Directory to save downloaded PDFs (default: downloads)'
    )
    parser.add_argument(
        '--format',
        type=str,
        choices=['csv', 'excel', 'json'],
        default='csv',
        help='Output format (default: csv)'
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Perform data validation and show results'
    )

    args = parser.parse_args()

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Initialize downloader and parser
    downloader = PDFDownloader(download_dir=args.download_dir)
    parser_obj = PDFParser()

    print(f"WSE Indices Weights Loader")
    print(f"Date: {args.date}")
    print(f"Output directory: {args.output_dir}")
    print("-" * 50)

    # Download PDFs
    if args.index:
        # Download specific index
        print(f"Downloading PDF for index: {args.index}")
        pdf_files = [downloader.download_specific_pdf(args.index, args.date)]
        pdf_files = [f for f in pdf_files if f]  # Remove None values
    else:
        # Download all available PDFs for the date
        print(f"Downloading all available PDFs for date: {args.date}")
        pdf_files = downloader.download_pdfs_for_date(args.date)

    if not pdf_files:
        print("No PDF files were downloaded. Please check the date or index name.")
        sys.exit(1)

    print(f"Downloaded {len(pdf_files)} PDF file(s)")

    # Process each PDF file
    all_results = []

    for pdf_file in pdf_files:
        print(f"\nProcessing: {os.path.basename(pdf_file)}")

        try:
            # Parse the PDF
            records = parser_obj.parse_pdf(pdf_file)

            if not records:
                print(f"  No data extracted from {pdf_file}")
                continue

            print(f"  Extracted {len(records)} records")

            # Validate data if requested
            if args.validate:
                validation_result = parser_obj.validate_data(records)
                print(
                    f"  Validation: {'PASS' if validation_result['valid'] else 'FAIL'}")
                print(
                    f"  Total share %: {validation_result['total_share_percent']:.4f}%")
                if validation_result['has_duplicates']:
                    print("  WARNING: Duplicate ISINs found")
                if validation_result['has_missing_data']:
                    print("  WARNING: Missing or invalid data found")

            # Convert to DataFrame
            df = parser_obj.to_dataframe(records)

            # Generate output filename
            base_name = os.path.splitext(os.path.basename(pdf_file))[0]

            # Save in requested format
            if args.format == 'csv':
                output_file = os.path.join(args.output_dir, f"{base_name}.csv")
                df.to_csv(output_file, index=False)
            elif args.format == 'excel':
                output_file = os.path.join(
                    args.output_dir, f"{base_name}.xlsx")
                df.to_excel(output_file, index=False)
            elif args.format == 'json':
                output_file = os.path.join(
                    args.output_dir, f"{base_name}.json")
                df.to_json(output_file, orient='records', indent=2)

            print(f"  Saved: {output_file}")
            all_results.append({
                'file': pdf_file,
                'records': len(records),
                'output': output_file,
                'validation': validation_result if args.validate else None
            })

        except Exception as e:
            print(f"  ERROR processing {pdf_file}: {e}")
            continue

    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)

    total_records = sum(result['records'] for result in all_results)
    print(f"Files processed: {len(all_results)}")
    print(f"Total records extracted: {total_records}")

    if args.validate:
        valid_files = sum(1 for result in all_results
                          if result['validation'] and result['validation']['valid'])
        print(f"Valid files: {valid_files}/{len(all_results)}")

    print(f"Output files saved in: {args.output_dir}")


if __name__ == "__main__":
    main()
