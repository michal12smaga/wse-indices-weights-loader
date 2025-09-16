"""
PDF parser module for WSE indices weights.
Extracts table data from PDF files containing stock indices information.
"""

import pdfplumber
import pandas as pd
import re
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass


@dataclass
class StockRecord:
    """Represents a single stock record from the index."""
    no: int
    isin: str
    company_name: str
    price_pln: float
    number_of_shares: int
    share_percent: float


class PDFParser:
    """Parses PDF files to extract stock index data."""

    def __init__(self):
        self.current_index_name = None
        self.current_date = None

    def parse_pdf(self, pdf_path: str) -> List[StockRecord]:
        """
        Parse a PDF file and extract stock records.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            List of StockRecord objects
        """
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
        # Based on analysis: Polish ISINs have PL + 0-6 letters + digits
        # Foreign ISINs have 2 letters + 10 alphanumeric characters

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

        # Check for Polish ISIN pattern first: PL + company identifier + check digit
        if potential_isin.startswith('PL'):
            rest = potential_isin[2:]
            # Polish pattern: PL + alphanumeric company identifier (9 chars) + check digit (1 char)
            # Company part can contain letters and numbers (e.g., 11BIT -> PL11BTS00015)
            # Total after PL should be exactly 10 characters
            if len(rest) == 10 and re.match(r'^[A-Z0-9]{9}\d$', rest):
                return True

        # Check for foreign ISIN pattern: 2 letters + 10 alphanumeric
        elif re.match(r'^[A-Z]{2}[A-Z0-9]{10}$', potential_isin):
            return True

        return False

    def _extract_metadata(self, text: str):
        """Extract index name and date from the text."""
        lines = text.split('\n')

        # Look for index name in the first few lines
        for line in lines[:10]:
            line = line.strip().upper()
            if any(index in line for index in ['WIG', 'MWIG', 'SWIG']):
                # Extract index name
                for word in line.split():
                    if any(index in word for index in ['WIG', 'MWIG', 'SWIG']):
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

    def _find_table_start(self, lines: List[str]) -> int:
        """Find the line where the table data starts."""
        # Look for table headers that indicate start of data
        header_patterns = [
            r'lp\.?\s+isin',  # "Lp. ISIN" or similar
            r'no\.?\s+isin',  # "No. ISIN" or similar
            r'numer\s+isin',  # "Numer ISIN"
            # Direct data line (number followed by ISIN)
            r'\d+\s+[A-Z]{2}\d{10}'
        ]

        for i, line in enumerate(lines):
            line_lower = line.lower().strip()

            # Check for header patterns
            for pattern in header_patterns[:-1]:
                if re.search(pattern, line_lower):
                    return i + 1  # Return next line after header

            # Check for direct data pattern (fallback)
            if re.search(header_patterns[-1], line):
                return i

        return -1

    def _parse_stock_line(self, line: str) -> Optional[StockRecord]:
        """
        Parse a single line of stock data.

        Expected format: No ISIN Company_Name Price(PLN) Number_of_shares Share(%)
        Strategy: Use comma-containing columns (price and share%) as anchors
        - Price: has comma, comes after company name
        - Share%: has comma, is always the last part  
        - Number of shares: everything between price and share%, no commas

        Examples:
        1 PLPKO0000016 PKOBP 59,3600 729 103 000 10,0000
        6 PLLPP0000011 LPP 17 340,0000 1 276 000 5,1123
        """
        # Skip lines that don't look like data
        if not re.match(r'^\s*\d+', line):
            return None

        # Clean the line
        line = line.strip()
        parts = line.split()

        if len(parts) < 6:  # Minimum expected parts
            return None

        try:
            # Extract ordinal number (first part)
            no = int(parts[0])

            # Extract ISIN code (second part, always at index 1)
            isin = parts[1]
            if not self._is_isin(isin):
                return None

            # Extract share percentage (last part, always has comma)
            share_percent_str = parts[-1]
            if ',' not in share_percent_str:
                return None
            share_percent = self._parse_decimal(share_percent_str)
            if share_percent is None:
                return None

            # Find the price column - scan from right to left looking for comma-containing parts
            # The rightmost comma part (before share%) should be the last part of the price
            price_end_idx = -1
            # Start before share%, go backwards to after ISIN
            for i in range(len(parts) - 2, 1, -1):
                if ',' in parts[i]:
                    price_end_idx = i
                    break

            if price_end_idx == -1:
                return None

            # Now find the start of the price - it could be multiple parts for large numbers
            # Work backwards from price_end_idx to find where price starts
            price_start_idx = price_end_idx
            for i in range(price_end_idx - 1, 1, -1):  # Go backwards from price_end
                # If this part is numeric (no comma) and the next part has comma,
                # this could be part of a multi-part price like "17 340,0000"
                if (self._is_numeric_part(parts[i]) and
                        i + 1 < len(parts) and ',' in parts[i + 1]):
                    price_start_idx = i
                else:
                    break

            # Extract price parts and combine them
            price_parts = parts[price_start_idx:price_end_idx + 1]
            price_str = ' '.join(price_parts)

            # For multi-part prices, we need to handle them specially
            # Example: "17 340,0000" should become "17340,0000"
            if len(price_parts) > 1:
                # Remove spaces except around the comma
                price_str = ''.join(price_parts[:-1]) + price_parts[-1]

            price_pln = self._parse_decimal(price_str)
            if price_pln is None or price_pln <= 0:
                return None

            # Company name is everything between ISIN and price start
            company_parts = parts[2:price_start_idx]
            company_name = ' '.join(company_parts).strip()

            # Number of shares is everything between price end and share percentage
            shares_parts = parts[price_end_idx + 1:-1]

            # All shares parts should be numeric (no commas)
            for part in shares_parts:
                if not self._is_numeric_part(part) or ',' in part:
                    return None

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

    def _is_isin(self, text: str) -> bool:
        """Check if text matches ISIN format."""
        if len(text) != 12:
            return False

        # Check if starts with two letters (country code)
        if not text[:2].isalpha():
            return False

        # For Polish ISINs, check specific pattern after country code
        if text.startswith('PL'):
            # Pattern: PL + alphanumeric company identifier (can include numbers like 11BIT)
            remaining = text[2:]
            # Must be exactly 10 characters and alphanumeric
            if len(remaining) != 10 or not remaining.isalnum():
                return False
            # Must end with at least one digit (check digit)
            if not remaining[-1].isdigit():
                return False

        # For non-Polish ISINs, rest should be alphanumeric with proper format
        else:
            remaining = text[2:]
            if len(remaining) != 10 or not remaining.isalnum():
                return False
            # Must have at least one digit in the remaining part
            if not any(c.isdigit() for c in remaining):
                return False

        return True

    def _is_numeric_part(self, text: str) -> bool:
        """Check if text is a numeric part (digits possibly with spaces)."""
        # Remove spaces and check if remaining chars are digits
        cleaned = text.replace(' ', '')
        return cleaned.isdigit()

    def _parse_decimal(self, text: str) -> Optional[float]:
        """Parse decimal number with comma as decimal separator."""
        try:
            # Replace comma with dot for float parsing
            normalized = text.replace(',', '.')
            return float(normalized)
        except ValueError:
            return None

    def _parse_shares_number(self, parts: List[str]) -> Optional[int]:
        """Parse number of shares which might be split by spaces (thousand separators)."""
        try:
            # Join all parts and remove spaces
            combined = ''.join(parts).replace(' ', '')
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

    def validate_data(self, records: List[StockRecord]) -> Dict[str, Any]:
        """
        Validate the extracted data.

        Returns:
            Dictionary with validation results
        """
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


if __name__ == "__main__":
    # Test the parser
    parser = PDFParser()
    print("PDF Parser module ready for testing")
