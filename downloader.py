import os
import requests
from urllib.parse import urlparse
import config
from config_manager import ConfigManager
import logging

class EarningsDocDownloader:
    def __init__(self, config_manager=None):
        self.storage_path = config.LOCAL_STORAGE_PATH
        # Initialize config manager
        self.config_manager = config_manager or ConfigManager()
        # Browser-like user agent to avoid 403 errors
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
        }
    
    def download_file(self, url, company, quarter, year, file_type):
        """
        Download a file from a URL and save it locally.
        
        Args:
            url (str): URL of the file to download
            company (str): Company name or ticker
            quarter (str): Quarter (Q1, Q2, Q3, Q4)
            year (str): Year
            file_type (str): Type of file (transcript, press_release, etc.)
            
        Returns:
            str: Path to the downloaded file
        """
        try:
            # Create a directory structure like downloads/amazon/2023_Q1/
            company_dir = os.path.join(self.storage_path, company.lower())
            period_dir = os.path.join(company_dir, f"{year}_{quarter}")
            
            if not os.path.exists(company_dir):
                os.makedirs(company_dir)
            if not os.path.exists(period_dir):
                os.makedirs(period_dir)
            
            # Get the filename from the URL or create one
            parsed_url = urlparse(url)
            if os.path.basename(parsed_url.path):
                filename = os.path.basename(parsed_url.path)
            else:
                # Create a filename if none is in the URL
                filename = f"{company.lower()}_{year}_{quarter}_{file_type}"
                
                # Add extension based on content-type
                try:
                    # Try with headers first
                    response = requests.head(url, headers=self.headers, timeout=10)
                    response.raise_for_status()
                except (requests.exceptions.RequestException, requests.exceptions.HTTPError):
                    # If head request fails, try a normal GET request just to check content type
                    response = requests.get(url, headers=self.headers, timeout=10, stream=True)
                    response.close()  # Close connection without downloading the whole file
                
                content_type = response.headers.get('Content-Type', '')
                if 'pdf' in content_type:
                    filename += '.pdf'
                elif 'html' in content_type:
                    filename += '.html'
                else:
                    filename += '.txt'
            
            # Path to save the file
            file_path = os.path.join(period_dir, filename)
            
            # Download the file if it doesn't exist
            if not os.path.exists(file_path):
                logging.info(f"Downloading {url} to {file_path}")
                
                # Try with headers first to avoid 403 errors
                session = requests.Session()
                session.headers.update(self.headers)
                
                try:
                    # Allow redirects and use a session for potential cookies
                    response = session.get(url, timeout=30, allow_redirects=True)
                    
                    # If we get a 403 even with headers, provide clear feedback
                    if response.status_code == 403:
                        logging.warning(f"Access forbidden (403) for {url}.")
                        logging.warning("This document requires login credentials or is behind a paywall.")
                        logging.warning("Consider manually downloading the document from the IR site.")
                        return None
                    
                    response.raise_for_status()
                    
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
                    logging.info(f"Successfully downloaded {url}")
                
                except requests.exceptions.HTTPError as e:
                    logging.error(f"HTTP Error: {e}")
                    if response.status_code == 404:
                        logging.error(f"The document was not found at {url}")
                    elif response.status_code == 403:
                        logging.error(f"Access denied to {url} - document likely requires authentication")
                    return None
                except requests.exceptions.ConnectionError:
                    logging.error(f"Connection Error: Could not connect to {url}")
                    return None
                except requests.exceptions.Timeout:
                    logging.error(f"Timeout Error: Request to {url} timed out")
                    return None
                except requests.exceptions.RequestException as e:
                    logging.error(f"Request Error: {e}")
                    return None
            else:
                logging.info(f"File already exists at {file_path}")
            
            return file_path
            
        except Exception as e:
            logging.error(f"Error downloading {url}: {str(e)}")
            return None
    
    def download_latest_earnings(self, ticker):
        """
        Download the latest earnings documents for a specific company based on the configuration.
        
        Args:
            ticker (str): Company ticker symbol (lowercase, e.g., 'amzn')
            
        Returns:
            dict: Paths to downloaded documents
        """
        # Get company info from config manager
        company_info = self.config_manager.get_company(ticker)
        if not company_info:
            logging.error(f"No configuration found for ticker {ticker}")
            return None
        
        # Get latest release information
        year, quarter, release_data = self.config_manager.get_latest_release(ticker)
        if not release_data:
            logging.error(f"No release data found for {ticker}")
            return None
        
        result = {
            'company': company_info['name'],
            'ticker': company_info['ticker'],
            'quarter': quarter,
            'year': year,
            'ir_site': company_info['ir_site'],
            'files': {}
        }
        
        # Download earnings release PDF if available
        if release_data.get('earnings_release'):
            pdf_url = release_data['earnings_release']
            # Skip if the URL is just the IR site (requires manual navigation)
            if pdf_url != company_info['ir_site']:
                pdf_path = self.download_file(
                    pdf_url,
                    ticker,
                    quarter,
                    year,
                    'earnings_release'
                )
                if pdf_path:
                    result['files']['earnings_release'] = {
                        'path': pdf_path,
                        'url': pdf_url
                    }
        
        # Download call transcript PDF if available
        if release_data.get('call_transcript'):
            transcript_url = release_data['call_transcript']
            transcript_path = self.download_file(
                transcript_url,
                ticker,
                quarter,
                year,
                'call_transcript'
            )
            if transcript_path:
                result['files']['call_transcript'] = {
                    'path': transcript_path,
                    'url': transcript_url
                }
        
        if not result['files']:
            logging.warning(f"\nNo documents were successfully downloaded for {company_info['name']} ({ticker.upper()})")
            logging.warning(f"Please check the investor relations site manually: {company_info['ir_site']}")
            logging.warning("Possible reasons for download failures:")
            logging.warning("1. The documents require login credentials or are behind a paywall")
            logging.warning("2. The URLs in the configuration are incorrect or outdated")
            logging.warning("3. The company website has strict security measures against automated downloads")
            logging.warning("\nAction required: Navigate to the IR site and download the documents manually.")
        
        return result
    
    def get_available_companies(self):
        """Returns a list of available company tickers from the configuration."""
        return list(self.config_manager.get_all_companies().keys())

    def _download_release_documents(self, company_ticker, year, quarter, release_data):
        """
        Download earnings release and call transcript documents for a specific release.
        
        Args:
            company_ticker (str): Company ticker symbol
            year (str): Release year
            quarter (str): Release quarter
            release_data (dict): Release data containing URLs
            
        Returns:
            dict: Download information including local paths and status
        """
        download_info = {
            'company_ticker': company_ticker,
            'year': year,
            'quarter': quarter,
            'download_success': False,
            'files': {}
        }
        
        download_dir = self._get_download_dir(company_ticker, year, quarter)
        
        # Download earnings release PDF if available
        if release_data.get('earnings_release'):
            pdf_url = release_data['earnings_release']
            pdf_filename = f"{company_ticker}_{year}_{quarter}_earnings_release"
            
            # Handle different file extensions
            extension = self._get_file_extension(pdf_url)
            if extension:
                pdf_filename += f".{extension}"
            elif pdf_url.lower().endswith('.pdf'):
                pdf_filename += ".pdf"
            else:
                pdf_filename += ".html"  # Default to HTML if no extension detected
            
            pdf_path = os.path.join(download_dir, pdf_filename)
            
            download_info['files']['earnings_release'] = {
                'url': pdf_url,
                'path': pdf_path,
                'success': self._download_file(pdf_url, pdf_path)
            }
        
        # Download call transcript PDF if available
        if release_data.get('call_transcript'):
            transcript_url = release_data['call_transcript']
            transcript_filename = f"{company_ticker}_{year}_{quarter}_call_transcript"
            
            # Handle different file extensions
            extension = self._get_file_extension(transcript_url)
            if extension:
                transcript_filename += f".{extension}"
            elif transcript_url.lower().endswith('.pdf'):
                transcript_filename += ".pdf"
            else:
                transcript_filename += ".html"  # Default to HTML if no extension detected
                
            transcript_path = os.path.join(download_dir, transcript_filename)
            
            download_info['files']['call_transcript'] = {
                'url': transcript_url,
                'path': transcript_path,
                'success': self._download_file(transcript_url, transcript_path)
            }
        
        # Mark overall success if at least one file was downloaded successfully
        for file_type, file_info in download_info['files'].items():
            if file_info['success']:
                download_info['download_success'] = True
                break
        
        return download_info 