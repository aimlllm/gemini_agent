import os
import requests
from urllib.parse import urlparse
import config
from config_manager import ConfigManager
import logging

class EarningsDocDownloader:
    def __init__(self, config_manager=None):
        # Try to use the configured storage path, but fall back to local directory if needed
        self.storage_path = config.LOCAL_STORAGE_PATH
        # Fallback: If the configured path is not writable, use a local directory
        if not os.access(os.path.dirname(self.storage_path) or '.', os.W_OK):
            logging.warning(f"Storage path {self.storage_path} is not writable")
            self.storage_path = os.path.join(os.getcwd(), 'downloads')
            logging.warning(f"Using local fallback: {self.storage_path}")
            
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
    
    def _create_directory_safely(self, directory):
        """Safely create a directory, handling errors gracefully."""
        if not os.path.exists(directory):
            try:
                os.makedirs(directory)
                return True
            except (OSError, PermissionError) as e:
                logging.error(f"Could not create directory {directory}: {e}")
                return False
        return True
    
    def download_file(self, url, ticker, year, quarter, doc_type):
        """
        Download a file from a URL and save it to the appropriate location.
        
        Args:
            url (str): URL to download
            ticker (str): Company ticker symbol
            year (str): Year of earnings release
            quarter (str): Quarter of earnings release
            doc_type (str): Type of document (earnings_release, call_transcript)
            
        Returns:
            str: Path to downloaded file, or None if download failed
        """
        # Clean ticker for directory name
        ticker = ticker.lower()
        
        # Create directory structure
        dir_path = os.path.join(self.storage_path, ticker, f"{year}_{quarter}")
        try:
            os.makedirs(dir_path, exist_ok=True)
        except (OSError, PermissionError) as e:
            logging.error(f"Could not create directory {dir_path}: {e}")
            return None
        
        # Extract filename from URL or generate one
            parsed_url = urlparse(url)
                filename = os.path.basename(parsed_url.path)
        
        # If filename is empty or doesn't have an extension, create a default one
        if not filename or '.' not in filename:
            extension = 'pdf' if 'pdf' in parsed_url.path.lower() else 'html'
            doc_type_name = 'Earnings-Release' if doc_type == 'earnings_release' else 'Earnings-Call-Transcript'
            filename = f"{ticker.upper()}-{quarter}-{year}-{doc_type_name}.{extension}"
        
        # Full path to save the file
        file_path = os.path.join(dir_path, filename)
            
        # If file already exists, skip download
        if os.path.exists(file_path):
            logging.info(f"File already exists at {file_path}")
            return file_path
        
        # Download the file
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
            }
            
            # Check if URL is accessible before downloading
            response = requests.head(url, headers=headers, timeout=10)
            
            if response.status_code == 403:
                # Handle forbidden access (common with SeekingAlpha)
                if 'seekingalpha.com' in url:
                    logging.warning(f"Access forbidden (403) for SeekingAlpha URL: {url}")
                    logging.warning("SeekingAlpha likely requires subscription. Skipping this document.")
                else:
                    logging.warning(f"Access forbidden (403) for URL: {url}")
                return None
                
            if response.status_code != 200:
                logging.error(f"URL returned status code {response.status_code}: {url}")
                        return None
                    
            # Proceed with download
            response = requests.get(url, headers=headers, timeout=30)
                    response.raise_for_status()
                    
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
            
            logging.info(f"Downloaded {url} to {file_path}")
            return file_path
            
        except requests.exceptions.HTTPError as e:
            if '403' in str(e):
                if 'seekingalpha.com' in url:
                    logging.warning(f"Access forbidden (403) for SeekingAlpha URL: {url}")
                    logging.warning("SeekingAlpha requires subscription. Skipping this document.")
                else:
                    logging.warning(f"Access forbidden (403) for URL: {url}")
            else:
                logging.error(f"HTTP error downloading {url}: {e}")
            return None
        except Exception as e:
            logging.error(f"Error downloading {url}: {e}")
            return None
    
    def download_latest_earnings(self, ticker):
        """
        Download the latest earnings documents for a company.
        
        Args:
            ticker (str): Company ticker symbol
            
        Returns:
            dict: Dictionary with downloaded file information
                 {
                     'quarter': quarter,
                     'year': year,
                     'files': {
                         'earnings_release': {'path': file_path, 'url': url},
                         'call_transcript': {'path': file_path, 'url': url}
                     }
                 }
        """
        # Get latest release info
        year, quarter, release_data = self.config_manager.get_latest_release(ticker)
        
        if not release_data:
            logging.error(f"No release data found for {ticker}")
            return None
        
        # Record of downloaded files
        downloaded_files = {}
        
        # Download each available document type
        for doc_type in ['earnings_release', 'call_transcript']:
            if doc_type in release_data and release_data[doc_type]:
                url = release_data[doc_type]
                try:
                    file_path = self.download_file(url, ticker, year, quarter, doc_type)
                    if file_path:
                        downloaded_files[doc_type] = {'path': file_path, 'url': url}
                    else:
                        logging.warning(f"Failed to download {doc_type} for {ticker} {quarter} {year}")
                except Exception as e:
                    # Log but don't crash on download errors
                    logging.warning(f"Error downloading {doc_type} for {ticker} {quarter} {year}: {str(e)}")
                    
        # Log warning if SeekingAlpha transcript couldn't be downloaded
        if 'call_transcript' in release_data and 'seekingalpha.com' in release_data['call_transcript'] and 'call_transcript' not in downloaded_files:
            logging.warning(f"SeekingAlpha transcript could not be accessed - this is normal as it requires a subscription.")
            logging.warning(f"Analysis will proceed with available documents only.")
            
        # Continue if we have at least one document
        if downloaded_files:
            return {
                'quarter': quarter,
                'year': year,
                'files': downloaded_files
            }
        else:
            logging.error(f"No documents could be downloaded for {ticker} {quarter} {year}")
            return None
    
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