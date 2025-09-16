#!/usr/bin/env python3
"""
Final corrected PDF parser for WSE indices.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import re
import pandas as pd
import pdfplumber
import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@dataclass
class StockRecord:
    """Represents a single stock record from the index."""
    no: int
    isin: str
    company_name: str
    price_pln: float
    number_of_shares: int
    share_percent: float


class FinalPDFParser:
    """Final corrected parser for WSE PDF files."""

    def __init__(self):
        self.current_index_name = None
        self.current_date = None

    def parse_pdf(self, pdf_path: str) -> List[StockRecord]:
        """Parse a PDF file and extract stock records."""
        records = []

        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                page_records = self._parse_page(page, page_num)
                records.extend(page_records)

        return records

    def _parse_page(self, page, page_num: int) -> List[StockRecord]:
        """Parse a single page and extract stock records."""
        records = []

        # Extract text from the page
        text = page.extract_text()
        if not text:
            return records

        # Try to extract index name and date from the first page
        if page_num == 0:
            self._extract_metadata(text)

        # Split text into lines
        lines = text.split('\n')

        # Process each line looking for stock data
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if this line looks like stock data
            if self._is_stock_data_line(line):
                record = self._parse_stock_line(line)
                if record:
                    records.append(record)

        return records

    def _is_stock_data_line(self, line: str) -> bool:
        """Check if a line contains stock data."""
        # Must start with a number and contain an ISIN pattern
        # Updated to handle both foreign ISINs (2 letters + 10 alphanumeric)
        # and Polish ISINs (PL + 3-10 letters + digits)

        # Check if starts with number
        if not re.match(r'^\d+\s+', line):
            return False

        # Split to get potential ISIN (second word)
        parts = line.split()
        if len(parts) < 2:
            return False

        potential_isin = parts[1]

        # Check if it looks like an ISIN (12 characters, uppercase)
        if len(potential_isin) != 12 or not potential_isin.isupper():
            return False

        # Check for foreign ISIN pattern: 2 letters + 10 alphanumeric
        if re.match(r'^[A-Z]{2}[A-Z0-9]{10}$', potential_isin):
            return True

        # Check for Polish ISIN pattern: PL + 3-10 letters + digits
        if potential_isin.startswith('PL'):
            rest = potential_isin[2:]
            # Look for pattern: letters followed by digits
            if re.match(r'^[A-Z]{3,10}\d+$', rest):
                return True

        return False

    def _extract_metadata(self, text: str):
        """Extract index name and date from the text."""
        lines = text.split('\n')

        # Look for index name in the first few lines
        for line in lines[:10]:
            line_upper = line.strip().upper()
            if 'WIG' in line_upper:
                # Try to extract the exact index name
                words = line_upper.split()
                for word in words:
                    if 'WIG' in word:
                        self.current_index_name = word
                        break
                break

        # Look for date pattern (DD.MM.YYYY)
        date_pattern = r'\d{2}\.\d{2}\.\d{4}'
        for line in lines[:20]:
            match = re.search(date_pattern, line)
            if match:
                self.current_date = match.group()
                break

    def _parse_stock_line(self, line: str) -> Optional[StockRecord]:
        """
        Parse a single line of stock data.
        Format: No ISIN Company_Name Price(PLN) Number_of_shares(with spaces) Share(%)
        Example: 1 PLPKO0000016 PKOBP 59,3600 729 103 000 10,0000
        """
        try:
            # Normalize multiple spaces to single spaces
            line = re.sub(r'\s+', ' ', line.strip())
            parts = line.split(' ')

            if len(parts) < 6:
                return None

            # Extract ordinal number (first part)
            no = int(parts[0])

            # Extract ISIN (second part)
            isin = parts[1]
            if not self._is_valid_isin(isin):
                return None

            # The last part is always the share percentage
            share_str = parts[-1]
            share_percent = self._parse_decimal(share_str)
            if share_percent is None:
                return None

            # Find the price - it's the first decimal number after the company name
            # Company name starts at index 2
            price_idx = -1
            for i in range(2, len(parts) - 1):
                if ',' in parts[i] and self._parse_decimal(parts[i]) is not None:
                    # This looks like a price (has comma decimal separator)
                    price_pln = self._parse_decimal(parts[i])
                    price_idx = i
                    break

            if price_idx == -1 or price_pln is None:
                return None

            # Company name is everything from index 2 to price_idx
            company_parts = parts[2:price_idx]
            company_name = ' '.join(company_parts).strip()

            # Shares are everything between price and share percentage
            shares_parts = parts[price_idx + 1:-1]
            number_of_shares = self._parse_shares_number(shares_parts)

            if number_of_shares is None or not company_name:
                return None

            return StockRecord(
                no=no,
                isin=isin,
                company_name=company_name,
                price_pln=price_pln,
                number_of_shares=number_of_shares,
                share_percent=share_percent
            )

        except (ValueError, IndexError) as e:
            return None

    def _is_valid_isin(self, text: str) -> bool:
        """Check if text looks like an ISIN code."""
        return len(text) == 12 and text[:2].isalpha() and text[2:].isalnum()

    def _parse_decimal(self, text: str) -> Optional[float]:
        """Parse decimal number with comma as decimal separator."""
        try:
            # Replace comma with dot for float parsing
            normalized = text.replace(',', '.')
            return float(normalized)
        except ValueError:
            return None

    def _parse_shares_number(self, parts: List[str]) -> Optional[int]:
        """Parse number of shares which might be split by spaces."""
        try:
            # Join all parts and remove spaces to get the full number
            combined = ''.join(parts)
            return int(combined)
        except ValueError:
            return None

    def to_dataframe(self, records: List[StockRecord]) -> pd.DataFrame:
        """Convert list of StockRecord to pandas DataFrame."""
        data = []
        for record in records:
            data.append({
                'No': record.no,
                'ISIN': record.isin,
                'Company_Name': record.company_name,
                'Price_PLN': record.price_pln,
                'Number_of_Shares': record.number_of_shares,
                'Share_Percent': record.share_percent
            })

        df = pd.DataFrame(data)

        # Add metadata if available
        if self.current_index_name:
            df['Index_Name'] = self.current_index_name
        if self.current_date:
            df['Date'] = self.current_date

        return df

    def validate_data(self, records: List[StockRecord]) -> Dict[str, any]:
        """Validate the extracted data."""
        if not records:
            return {'valid': False, 'error': 'No records found'}

        # Calculate total share percentage
        total_shares = sum(record.share_percent for record in records)

        # Check if total is approximately 100%
        share_valid = abs(total_shares - 100.0) < 0.1  # Allow 0.1% deviation

        # Check for duplicate ISINs
        isins = [record.isin for record in records]
        unique_isins = set(isins)
        duplicates = len(isins) != len(unique_isins)

        # Check for missing data
        missing_data = any(
            not record.isin or
            not record.company_name or
            record.price_pln <= 0 or
            record.number_of_shares <= 0 or
            record.share_percent <= 0
            for record in records
        )

        return {
            'valid': share_valid and not duplicates and not missing_data,
            'total_share_percent': total_shares,
            'share_percent_valid': share_valid,
            'has_duplicates': duplicates,
            'has_missing_data': missing_data,
            'record_count': len(records)
        }


def test_final_parser():
    """Test the final corrected parser."""
    print("Testing Final Corrected PDF Parser")
    print("=" * 50)

    parser = FinalPDFParser()
    pdf_file = "downloads/2024_06_21_WIG.pdf"

    if not os.path.exists(pdf_file):
        print(f"PDF file not found: {pdf_file}")
        assert False, f"PDF file not found: {pdf_file}"

    # Parse the PDF
    print("Parsing PDF...")
    records = parser.parse_pdf(pdf_file)

    assert records, "No records extracted from PDF"
    print(f"Extracted {len(records)} records")

    # Show first few records
    print("\nFirst 15 records:")
    for record in records[:15]:
        print(f"  {record.no:3d}. {record.isin} {record.company_name[:20]:20s} "
              f"{record.price_pln:10.4f} PLN {record.number_of_shares:12,d} shares "
              f"{record.share_percent:7.4f}%")

    if len(records) > 15:
        print(f"\n... and {len(records) - 15} more records")

    # Validate data
    validation = parser.validate_data(records)
    print(f"\nValidation:")
    print(f"  Valid: {'YES' if validation['valid'] else 'NO'}")
    print(f"  Total share %: {validation['total_share_percent']:.4f}%")
    print(f"  Records: {validation['record_count']}")

    if validation['has_duplicates']:
        print("  WARNING: Duplicate ISINs found")
    if validation['has_missing_data']:
        print("  WARNING: Missing or invalid data found")

    # Show a few specific details
    if records:
        print(f"\nMetadata:")
        print(f"  Index: {parser.current_index_name}")
        print(f"  Date: {parser.current_date}")

    # Convert to DataFrame and save
    df = parser.to_dataframe(records)

    # Create output directory
    os.makedirs('output', exist_ok=True)

    # Save as CSV
    csv_file = 'output/2024_06_21_WIG_final.csv'
    df.to_csv(csv_file, index=False)
    print(f"\nSaved to: {csv_file}")

    # Also save as Excel for easier viewing
    excel_file = 'output/2024_06_21_WIG_final.xlsx'
    df.to_excel(excel_file, index=False)
    print(f"Saved to: {excel_file}")

    # Test completed successfully - no return needed for pytest


if __name__ == "__main__":
    try:
        test_final_parser()
        print("\n" + "=" * 50)
        print("TEST COMPLETED SUCCESSFULLY!")
        print("=" * 50)
    except (AssertionError, Exception) as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)
