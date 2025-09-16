#!/usr/bin/env python3
"""
Unit tests for PDF parser functionality.
"""

from pdf_parser import PDFParser, StockRecord
import pytest
import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestPDFParser:
    """Test cases for PDFParser class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = PDFParser()

    def test_isin_validation_polish_valid(self):
        """Test valid Polish ISIN validation."""
        valid_polish_isins = [
            "PLPKO0000016",  # PKO BP
            "PLPEKAO00016",  # Pekao
            "PLBZ00000044",  # BZ WBK
            "PL11BTS00015",  # 11 BIT
            "PLR220000018",  # R22
        ]

        for isin in valid_polish_isins:
            assert self.parser._is_isin(
                isin), f"Valid Polish ISIN {isin} should pass validation"

    def test_isin_validation_foreign_valid(self):
        """Test valid foreign ISIN validation."""
        valid_foreign_isins = [
            "LU2237380790",  # Luxembourg
            "ES0105375002",  # Spain
            "US0378331005",  # Apple
            "GB0002875804",  # British Petroleum
        ]

        for isin in valid_foreign_isins:
            assert self.parser._is_isin(
                isin), f"Valid foreign ISIN {isin} should pass validation"

    def test_isin_validation_invalid(self):
        """Test invalid ISIN validation."""
        invalid_isins = [
            "INVALID123",     # Wrong length
            "PLABCDEFGHA",    # Ends with letter
            "12ABCDEF1234",   # Starts with numbers
            "PL123456789A",   # Invalid format
            "",               # Empty string
            "TOOLONGISINNUMB",  # Too long
        ]

        for isin in invalid_isins:
            assert not self.parser._is_isin(
                isin), f"Invalid ISIN {isin} should fail validation"

    def test_stock_data_line_detection(self):
        """Test detection of stock data lines."""
        valid_lines = [
            "1 PLPKO0000016 PKO BP 45,86 12 500 000 14,2345",
            "6 PLLPP0000011 LPP 17 340,0000 1 276 000 5,1123",
            "25 PL11BTS00015 11 BIT 123,45 1 000 000 2,5000",
        ]

        invalid_lines = [
            "Lp. ISIN Nazwa Price Shares %",  # Header
            "Total: 100.0000%",               # Summary
            "",                               # Empty
            "Some random text",               # Non-data
        ]

        for line in valid_lines:
            assert self.parser._is_stock_data_line(
                line), f"Valid data line should be detected: {line}"

        for line in invalid_lines:
            assert not self.parser._is_stock_data_line(
                line), f"Invalid data line should be rejected: {line}"

    def test_parse_stock_line_lpp(self):
        """Test parsing of LPP line specifically (regression test)."""
        lpp_line = "6 PLLPP0000011 LPP 17 340,0000 1 276 000 5,1123"
        record = self.parser._parse_stock_line(lpp_line)

        assert record is not None, "LPP line should parse successfully"
        assert record.no == 6
        assert record.isin == "PLLPP0000011"
        assert record.company_name == "LPP", f"Company name should be 'LPP', got '{record.company_name}'"
        assert abs(record.price_pln -
                   17340.0000) < 0.0001, f"Price should be 17340.0000, got {record.price_pln}"
        assert record.number_of_shares == 1276000
        assert abs(record.share_percent - 5.1123) < 0.0001

    def test_parse_stock_line_11bit(self):
        """Test parsing of 11 BIT line (alphanumeric ISIN test)."""
        bit_line = "25 PL11BTS00015 11 BIT 123,45 1 000 000 2,5000"
        record = self.parser._parse_stock_line(bit_line)

        assert record is not None, "11 BIT line should parse successfully"
        assert record.no == 25
        assert record.isin == "PL11BTS00015"
        assert record.company_name == "11 BIT"
        assert abs(record.price_pln - 123.45) < 0.01
        assert record.number_of_shares == 1000000
        assert abs(record.share_percent - 2.5000) < 0.0001

    def test_parse_stock_line_simple(self):
        """Test parsing of simple stock line."""
        simple_line = "1 PLPKO0000016 PKO BP 45,86 12 500 000 14,2345"
        record = self.parser._parse_stock_line(simple_line)

        assert record is not None, "Simple line should parse successfully"
        assert record.no == 1
        assert record.isin == "PLPKO0000016"
        assert record.company_name == "PKO BP"
        assert abs(record.price_pln - 45.86) < 0.01
        assert record.number_of_shares == 12500000
        assert abs(record.share_percent - 14.2345) < 0.0001

    def test_numeric_part_detection(self):
        """Test numeric part detection."""
        numeric_parts = [
            "123",
            "1 234",
            "12 345 678",
            "0",
        ]

        non_numeric_parts = [
            "ABC",
            "12,34",
            "123.45",
            "12A34",
            "",
        ]

        for part in numeric_parts:
            assert self.parser._is_numeric_part(
                part), f"'{part}' should be detected as numeric"

        for part in non_numeric_parts:
            assert not self.parser._is_numeric_part(
                part), f"'{part}' should not be detected as numeric"


if __name__ == "__main__":
    pytest.main([__file__])
