import json
import os
import logging
from datetime import datetime
import config

class ConfigManager:
    """
    Manages the company configuration data stored in JSON format.
    Acts as a bridge between the downloaders and analyzers.
    """
    
    def __init__(self, config_file=None):
        self.config_file = config_file or config.COMPANY_CONFIG_PATH
        self.config_data = self._load_config()
    
    def _load_config(self):
        """Load configuration from JSON file."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            else:
                logging.warning(f"Config file {self.config_file} not found. Creating empty config.")
                empty_config = {
                    "companies": {},
                    "meta": {
                        "last_updated": datetime.now().isoformat(),
                        "version": "1.0.0"
                    }
                }
                self._save_config(empty_config)
                return empty_config
        except json.JSONDecodeError as e:
            logging.error(f"Error parsing JSON from {self.config_file}: {str(e)}")
            raise
    
    def _save_config(self, config_data=None):
        """Save configuration to JSON file."""
        if config_data is None:
            config_data = self.config_data
        
        # Update metadata
        config_data["meta"]["last_updated"] = datetime.now().isoformat()
        
        with open(self.config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
    
    def get_all_companies(self):
        """Get information about all companies."""
        return self.config_data.get("companies", {})
    
    def get_company(self, ticker):
        """Get information about a specific company."""
        return self.config_data.get("companies", {}).get(ticker.lower())
    
    def get_latest_release(self, ticker):
        """
        Get the latest release information for a company.
        Returns a tuple of (year, quarter, release_data) for the latest release.
        """
        company = self.get_company(ticker)
        if not company:
            return None, None, None
        
        releases = company.get("releases", {})
        if not releases:
            return None, None, None
        
        # Find the most recent year
        years = sorted(releases.keys(), reverse=True)
        if not years:
            return None, None, None
        
        latest_year = years[0]
        quarters = releases[latest_year]
        
        # Find the most recent quarter with a date (not expected_date)
        # Instead of alphabetical sorting, let's find the quarter with the most recent actual date
        latest_quarter = None
        latest_date = None
        latest_data = None
        
        for quarter, data in quarters.items():
            if "date" in data and data["date"]:
                try:
                    # Parse the date to compare chronologically
                    from datetime import datetime
                    # Handle various date formats like "March 10, 2025", "June 11, 2025", etc.
                    quarter_date = datetime.strptime(data["date"], "%B %d, %Y")
                    
                    if latest_date is None or quarter_date > latest_date:
                        latest_date = quarter_date
                        latest_quarter = quarter
                        latest_data = data
                except (ValueError, TypeError) as e:
                    # If date parsing fails, log and skip this quarter
                    logging.warning(f"Could not parse date '{data['date']}' for {ticker} {quarter}: {e}")
                    continue
        
        if latest_quarter and latest_data:
            return latest_year, latest_quarter, latest_data
        
        # If no quarters have a parseable date, fall back to alphabetical sorting
        for quarter, data in sorted(quarters.items(), reverse=True):
            if "date" in data:
                return latest_year, quarter, data
        
        # If no quarters have a date, return the first quarter info as upcoming
        first_quarter = sorted(quarters.keys())[0]
        return latest_year, first_quarter, quarters[first_quarter]
    
    def add_or_update_company(self, ticker, name, ir_site):
        """Add a new company or update an existing one."""
        ticker = ticker.lower()
        if ticker not in self.config_data.get("companies", {}):
            self.config_data.setdefault("companies", {})[ticker] = {
                "name": name,
                "ticker": ticker.upper(),
                "ir_site": ir_site,
                "releases": {}
            }
        else:
            # Update existing company info
            self.config_data["companies"][ticker]["name"] = name
            self.config_data["companies"][ticker]["ticker"] = ticker.upper()
            self.config_data["companies"][ticker]["ir_site"] = ir_site
        
        self._save_config()
        return self.config_data["companies"][ticker]
    
    def add_or_update_release(self, ticker, year, quarter, release_data):
        """
        Add or update a release for a company.
        
        Args:
            ticker (str): Company ticker symbol
            year (str): Year of the release (e.g., "2025" or "FY25")
            quarter (str): Quarter identifier (e.g., "Q1", "Q2")
            release_data (dict): Release data containing info like date, time, URLs
        
        Returns:
            dict: Updated release data
        """
        ticker = ticker.lower()
        company = self.get_company(ticker)
        
        if not company:
            raise ValueError(f"Company with ticker {ticker} not found")
        
        # Ensure releases structure exists
        if "releases" not in company:
            company["releases"] = {}
        
        if year not in company["releases"]:
            company["releases"][year] = {}
        
        company["releases"][year][quarter] = release_data
        self._save_config()
        
        return company["releases"][year][quarter]
    
    def remove_company(self, ticker):
        """Remove a company from the configuration."""
        ticker = ticker.lower()
        if ticker in self.config_data.get("companies", {}):
            del self.config_data["companies"][ticker]
            self._save_config()
            return True
        return False
    
    def reload_config(self):
        """Reload configuration from file."""
        self.config_data = self._load_config()
        return self.config_data 