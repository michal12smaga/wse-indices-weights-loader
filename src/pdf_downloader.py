"""
PDF downloader module for WSE indices weights.
Downloads PDF files from GPW Benchmark website.
"""

import os
import requests
from urllib.parse import urljoin, urlparse
from typing import List, Dict
import re


class PDFDownloader:
    """Downloads PDF files from GPW Benchmark website."""

    BASE_URL = "https://gpwbenchmark.pl"
    HISTORICAL_URL = "https://gpwbenchmark.pl/historyczne-portfele-indeksow"
    PDF_BASE_URL = "https://gpwbenchmark.pl/pub/BENCHMARK/files/PDF/historyczne/"

    def __init__(self, download_dir: str = "downloads"):
        """Initialize downloader with download directory."""
        self.download_dir = download_dir
        os.makedirs(download_dir, exist_ok=True)

    def get_pdf_urls_for_date(self, date_str: str) -> List[str]:
        """
        Get all PDF URLs for a specific date.

        Args:
            date_str: Date string in format YYYY_MM_DD (e.g., "2024_06_21")

        Returns:
            List of PDF URLs for the given date
        """
        # Common index names that might have PDFs
        index_names = [
            "WIG", "WIG20", "WIG30", "mWIG40", "sWIG80",
            "WIG-DIV", "WIG-ESG", "WIGtech", "WIG-CHEMIA",
            "WIG-ENERGY", "WIG-MEDIA", "WIG-TELKOM", "WIG-BANKI",
            "WIG-BUDOW", "WIG-GORNIC", "WIG-NRCHOM", "WIG-PALIWA",
            "WIG-SPOZYW", "WIG-TELKOM", "WIG-TRANSPORT"
        ]

        pdf_urls = []
        for index_name in index_names:
            url = f"{self.PDF_BASE_URL}{date_str}_{index_name}.pdf"
            if self._url_exists(url):
                pdf_urls.append(url)

        return pdf_urls

    def _url_exists(self, url: str) -> bool:
        """Check if URL exists by making a HEAD request."""
        try:
            response = requests.head(url, timeout=10)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def download_pdf(self, url: str) -> str:
        """
        Download a PDF file from URL.

        Args:
            url: URL of the PDF file

        Returns:
            Local file path of downloaded PDF
        """
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Extract filename from URL
            filename = os.path.basename(urlparse(url).path)
            file_path = os.path.join(self.download_dir, filename)

            with open(file_path, 'wb') as f:
                f.write(response.content)

            print(f"Downloaded: {filename}")
            return file_path

        except requests.RequestException as e:
            print(f"Error downloading {url}: {e}")
            return None

    def download_pdfs_for_date(self, date_str: str) -> List[str]:
        """
        Download all PDFs for a specific date.

        Args:
            date_str: Date string in format YYYY_MM_DD

        Returns:
            List of local file paths of downloaded PDFs
        """
        urls = self.get_pdf_urls_for_date(date_str)
        downloaded_files = []

        print(f"Found {len(urls)} PDF files for date {date_str}")

        for url in urls:
            file_path = self.download_pdf(url)
            if file_path:
                downloaded_files.append(file_path)

        return downloaded_files

    def download_specific_pdf(self, index_name: str, date_str: str) -> str:
        """
        Download a specific PDF for an index and date.

        Args:
            index_name: Name of the index (e.g., "WIG", "WIG20")
            date_str: Date string in format YYYY_MM_DD

        Returns:
            Local file path of downloaded PDF or None if failed
        """
        url = f"{self.PDF_BASE_URL}{date_str}_{index_name}.pdf"
        return self.download_pdf(url)


if __name__ == "__main__":
    # Test the downloader
    downloader = PDFDownloader()

    # Download the example WIG file
    file_path = downloader.download_specific_pdf("WIG", "2024_06_21")
    if file_path:
        print(f"Successfully downloaded: {file_path}")
    else:
        print("Failed to download the example file")
