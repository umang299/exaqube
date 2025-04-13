import os
import sys
import time
import requests
import logging
from typing import List, Optional, Dict, Any


# Setup logging to a file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='app.log',        # Logs will be saved to 'app.log'
    filemode='a'               # Append mode (use 'w' to overwrite on each run)
)

logger = logging.getLogger(__name__)

cwd = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(cwd)

from src.models.config import Config
from src.models.scrapper import TariffEntry

cfg = Config.from_yaml(filepath=os.path.join(
                cwd, 'src', 'config.yaml'
            ))


class Scraper:
    """
    A scraper for retrieving shipping tariff data from COSCO Shipping's website.
    
    This class handles fetching tariff information and downloading associated PDF files.
    """

    def __init__(self):
        """
        Initialize the scraper with request headers and output directory.
        
        Args:
            output_dir: Directory where PDFs will be saved, defaults to ./downloads
        """
        self._request_header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://elines.coscoshipping.com/ebusiness/demurrageDetentionTariff"
        }

        self._download_header =  {
                "Accept": "application/json, text/plain, */*",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Accept-Language": "en-US,en;q=0.9,en-IN;q=0.8",
                "Connection": "keep-alive",
                "Host": "elines.coscoshipping.com",
                "Referer": "https://elines.coscoshipping.com/ebusiness/demurrageDetentionTariff",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, \
                    like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0"
            }


        # Set up output directory
        self.output_dir = cfg.scrapper.output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def fetch_tariff_info(self, country: str) -> Optional[TariffEntry]:
        """
        Fetch tariff information for a specific country.
        
        Args:
            country: The country to fetch tariff information for
            
        Returns:
            TariffEntry object if successful, None otherwise
        """
        try:
            timestamp = int(time.time() * 1000)
            info_url = f"{cfg.scrapper.url}?country={country}&timestamp={timestamp}"


            logger.info("Fetching tariff info for %s from %s", country, info_url)
            info_resp = requests.get(url=info_url, timeout=60)

            if info_resp.status_code != 200 and info_resp.status_code != 403:
                logger.error("Failed to fetch tariff info for %s. Status code: %s",
                            country, info_resp.status_code)
                return None

            if info_resp.status_code == 403:
                headers = {
                        "Accept": "application/json",
                        "Connection": "keep-alive",
                        "Cache-Control": "no-cache",
                        "Pragma": "no-cache",
                        "X-Content-Type-Options": "nosniff",
                        "X-XSS-Protection": "1; mode=block",
                        "X-Frame-Options": "ALLOWALL",
                        "User-Agent": "Mozilla/5.0",  # Add a user-agent for compatibility
                    }
                info_resp = requests.get(url=info_url, headers=headers, timeout=60)

            data = info_resp.json()

            # Check if we got a valid response code from the API
            if data.get('code') != '200':
                logger.error("API returned error code %s for %s: %s",
                            data.get('code', 'unknown'), country, data.get('message', 'No message'))
                return None

            # Handle the case where data['data']['content'] is None
            if not data.get('data') or data.get('data', {}).get('content') is None:
                logger.warning("No content found for %s - API returned empty result", country)
                return None

            tariff_data = TariffEntry.from_dict(data['data']['content'])
            logger.info("Successfully fetched tariff info for %s", country)
            return tariff_data

        except requests.RequestException as e:
            logger.error("Request error fetching tariff info for %s: %s", country, str(e))
            return None
        except ValueError as e:
            logger.error("JSON parsing error for %s: %s", country, str(e))
            return None
        except Exception as e:
            logger.error("Unexpected error fetching tariff info for %s: %s", country, str(e))
            return None

    def download_pdf(self, pdf_uuid: str, output_path: str) -> bool:
        """
        Download a PDF file by its UUID.
        
        Args:
            pdf_uuid: UUID of the PDF to download
            output_path: Path where the PDF will be saved
            
        Returns:
            bool: True if download was successful, False otherwise
        """
        try:
            timestamp = int(time.time() * 1000)
            pdf_url = f"{cfg.scrapper.download_link}?id={pdf_uuid}&timestamp={timestamp}"

            logger.info("Downloading PDF from %s to %s", pdf_url, output_path)

            response = requests.get(
                url=pdf_url,
                headers=self._download_header,
                timeout=30,
                stream=True  # Stream the response for large files
            )

            if response.status_code != 200:
                logger.error("Failed to download PDF. Status code: %s", response.status_code)
                return False

            # Check if content is actually a PDF
            if response.headers.get('content-type') != 'application/*;charset=utf-8':
                logger.error("Downloaded content is not a PDF: %s",
                             response.headers.get('content-type'))
                return False

            # Write the PDF content to file
            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info("Successfully downloaded PDF to %s", output_path)
            return True

        except requests.RequestException as e:
            logger.error("Request error downloading PDF: %s", str(e))
            return False
        except IOError as e:
            logger.error("File I/O error: %s", str(e))
            return False
        except Exception as e:
            logger.error("Unexpected error downloading PDF: %s", str(e))
            return False

    def download_tariff_pdfs(self, tariff_data: TariffEntry) -> Dict[str, bool]:
        """
        Download both inbound and outbound PDF files for a tariff entry.
        
        Args:
            tariff_data: Tariff entry containing PDF UUIDs and names
            
        Returns:
            Dictionary indicating which PDFs were successfully downloaded
        """
        results = {
            "inbound": False,
            "outbound": False
        }

        # Create country-specific directory
        country_dir = os.path.join(self.output_dir,tariff_data.country)
        os.makedirs(country_dir, exist_ok=True)

        # Download inbound PDF
        if tariff_data.inIddsPdfUuid:
            inbound_path = os.path.join(country_dir, tariff_data.inPdfName)
            results["inbound"] = self.download_pdf(tariff_data.inIddsPdfUuid, inbound_path)
        else:
            logger.warning("No inbound PDF UUID for %s", tariff_data.country)

        # Download outbound PDF
        if tariff_data.outIddsPdfUuid:
            outbound_path = os.path.join(country_dir, tariff_data.outPdfName)
            results["outbound"] = self.download_pdf(tariff_data.outIddsPdfUuid, outbound_path)
        else:
            logger.warning("No outbound PDF UUID for %s", tariff_data.country)

        return results

    def run(self, country: str) -> Dict[str, Dict[str, Any]]:
        """
        Run the scraper for multiple countries.
        
        Args:
            countries: List of country names to scrape
            
        Returns:
            Dictionary with results for each country
        """
        results = dict()
        time.sleep(30)
        logger.info("Processing country: %s", country)
        results[country] = {
                                "status": "failure",
                                "tariff_data": None,
                                "downloads": {}
                            }
        # Fetch tariff info
        tariff_data = self.fetch_tariff_info(country=country)
        if not tariff_data:
            return None

        results[country]["tariff_data"] = tariff_data

        # Download PDFs
        download_results = self.download_tariff_pdfs(tariff_data=tariff_data)
        results[country]["downloads"] = download_results

        if download_results["inbound"] or download_results["outbound"]:
            results[country]["status"] = "success"

        return results
