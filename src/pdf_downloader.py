"""
PDF downloader module for WSE indices weights.
Downloads PDF files from GPW Benchmark website.
Enhanced v0.2: Scrapes ALL available PDFs from the website.
"""

import os
import requests
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Tuple
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta


class PDFDownloader:
    """Downloads PDF files from GPW Benchmark website."""

    BASE_URL = "https://gpwbenchmark.pl"
    HISTORICAL_URL = "https://gpwbenchmark.pl/historyczne-portfele-indeksow"
    PDF_BASE_URL = "https://gpwbenchmark.pl/pub/BENCHMARK/files/PDF/historyczne/"

    def __init__(self, download_dir: str = "downloads"):
        """Initialize downloader with download directory."""
        self.download_dir = download_dir
        os.makedirs(download_dir, exist_ok=True)

        # Create session with retry configuration
        self.session = requests.Session()

        # Set a user agent to avoid blocking
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })

    def discover_all_pdfs(self) -> Dict[str, List[str]]:
        """
        Discover all available PDF files by scraping the website.

        Returns:
            Dict mapping dates to lists of PDF URLs available for that date
        """
        print("Discovering all available PDF files from GPW Benchmark...")

        try:
            # Access the historical page to find available dates/indices
            response = self.session.get(self.HISTORICAL_URL, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for links to PDF files or date references
            pdf_links = {}

            # Look for direct PDF links in the HTML
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.endswith('.pdf') and 'historyczne' in href:
                    full_url = urljoin(self.BASE_URL, href)
                    # Extract date from filename
                    filename = os.path.basename(href)
                    date_match = re.search(r'(\d{4}_\d{2}_\d{2})', filename)
                    if date_match:
                        date = date_match.group(1)
                        if date not in pdf_links:
                            pdf_links[date] = []
                        pdf_links[date].append(full_url)

            # Also look for any date patterns in text that might indicate available files
            page_text = soup.get_text()
            date_patterns = re.findall(r'\d{4}_\d{2}_\d{2}', page_text)

            # For each date found, try to construct URLs for common indices
            common_indices = ["WIG", "WIG20", "WIG30", "mWIG40", "sWIG80"]
            for date_str in set(date_patterns):
                if date_str not in pdf_links:
                    pdf_links[date_str] = []

                # Only check a few common indices to avoid being too aggressive
                for index_name in common_indices:
                    url = f"{self.PDF_BASE_URL}{date_str}_{index_name}.pdf"
                    if self._url_exists(url):
                        pdf_links[date_str].append(url)

                # Remove empty date entries
                if not pdf_links[date_str]:
                    del pdf_links[date_str]

            total_pdfs = sum(len(urls) for urls in pdf_links.values())
            print(
                f"Discovered {total_pdfs} PDF files across {len(pdf_links)} dates")

            return pdf_links

        except Exception as e:
            print(f"Error discovering PDFs: {e}")
            # Return empty dict instead of falling back to aggressive discovery
            return {}

    def get_all_available_dates(self) -> List[str]:
        """
        Get all dates that have PDF files available.

        Returns:
            List of date strings in YYYY_MM_DD format
        """
        all_pdfs = self.discover_all_pdfs()
        return sorted(all_pdfs.keys())

    def get_pdf_urls_for_date(self, date_str: str) -> List[str]:
        """
        Get all PDF URLs for a specific date.

        Args:
            date_str: Date string in format YYYY_MM_DD (e.g., "2024_06_21")

        Returns:
            List of PDF URLs for the given date
        """
        all_pdfs = self.discover_all_pdfs()
        return all_pdfs.get(date_str, [])

    def download_all_available_pdfs(self) -> Dict[str, List[str]]:
        """
        Download ALL available PDF files from the website.

        Returns:
            Dict mapping dates to lists of local file paths of downloaded PDFs
        """
        all_pdfs = self.discover_all_pdfs()
        downloaded_files = {}

        total_files = sum(len(urls) for urls in all_pdfs.values())
        print(f"Starting download of {total_files} PDF files...")

        downloaded_count = 0
        for date_str, urls in all_pdfs.items():
            downloaded_files[date_str] = []
            print(f"\nDownloading PDFs for {date_str}...")

            for url in urls:
                file_path = self.download_pdf(url)
                if file_path:
                    downloaded_files[date_str].append(file_path)
                    downloaded_count += 1
                    print(
                        f"Progress: {downloaded_count}/{total_files} files downloaded")

        print(
            f"\nDownload complete! Downloaded {downloaded_count} files across {len(downloaded_files)} dates")
        return downloaded_files

    def _url_exists(self, url: str) -> bool:
        """Check if URL exists by making a HEAD request with robust error handling."""
        try:
            response = self.session.head(url, timeout=10)
            return response.status_code == 200
        except (requests.RequestException, ConnectionError, TimeoutError) as e:
            # Log the specific error but don't crash
            print(f"Network error checking {url}: {type(e).__name__}")
            return False

    def download_pdf(self, url: str) -> str | None:
        """
        Download a PDF file from URL.

        Args:
            url: URL of the PDF file

        Returns:
            Local file path of downloaded PDF or None if failed
        """
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            # Extract filename from URL
            filename = os.path.basename(urlparse(url).path)
            file_path = os.path.join(self.download_dir, filename)

            with open(file_path, 'wb') as f:
                f.write(response.content)

            print(f"Downloaded: {filename}")
            return file_path

        except (requests.RequestException, ConnectionError, TimeoutError) as e:
            print(f"Error downloading {url}: {type(e).__name__} - {e}")
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

    def download_specific_pdf(self, index_name: str, date_str: str) -> str | None:
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
