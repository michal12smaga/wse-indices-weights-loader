#!/usr/bin/env python3
"""
Test the fixed parser with LPP and ISIN validation improvements.
"""

from pdf_parser import PDFParser
import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def test_lpp_parsing():
    """Test that LPP parsing is now correct."""

    parser = PDFParser()

    # Test the problematic LPP line
    lpp_line = "6 PLLPP0000011 LPP 17 340,0000 1 276 000 5,1123"

    print("Testing LPP parsing fix:")
    print("=" * 50)
    print(f"Line: {lpp_line}")

    record = parser._parse_stock_line(lpp_line)

    if record:
        print(f"✓ SUCCESS:")
        print(f"  No: {record.no}")
        print(f"  ISIN: {record.isin}")
        print(f"  Company: '{record.company_name}'")
        print(f"  Price: {record.price_pln:,.4f} PLN")
        print(f"  Shares: {record.number_of_shares:,}")
        print(f"  Share %: {record.share_percent:.4f}%")

        # Check if company name is correct (should be just "LPP")
        if record.company_name == "LPP":
            print(f"✓ Company name correctly parsed!")
        else:
            print(
                f"✗ Company name issue: got '{record.company_name}', expected 'LPP'")

        # Check if price is correct (should be 17340.0000)
        if abs(record.price_pln - 17340.0000) < 0.0001:
            print(f"✓ Price correctly parsed!")
        else:
            print(
                f"✗ Price issue: got {record.price_pln}, expected 17340.0000")
    else:
        print(f"✗ FAILED to parse")


def test_isin_validation():
    """Test ISIN validation with various patterns."""

    parser = PDFParser()

    # Test various ISIN patterns
    test_isins = [
        ("PLPKO0000016", True, "Polish ISIN - 3 letters"),
        ("PLPEKAO00016", True, "Polish ISIN - 5 letters"),
        ("PLBZ00000044", True, "Polish ISIN - 2 letters"),
        ("PL11BTS00015", True, "Polish ISIN - 11BIT with numbers"),
        ("PLR220000018", True, "Polish ISIN - 1 letter + numbers"),
        ("LU2237380790", True, "Foreign ISIN"),
        ("ES0105375002", True, "Foreign ISIN"),
        ("INVALID123", False, "Invalid - wrong length (9 chars)"),
        ("PLABCDEFGHA", False, "Invalid - ends with letter, not digit"),
        ("PL123456789A", False, "Invalid - ends with letter"),
    ]

    print("\nTesting ISIN validation:")
    print("=" * 50)

    for isin, expected, description in test_isins:
        result = parser._is_isin(isin)
        status = "✓" if result == expected else "✗"
        print(f"{status} {isin}: {result} ({description})")


if __name__ == "__main__":
    test_lpp_parsing()
    test_isin_validation()
