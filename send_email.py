#!/usr/bin/env python3
"""
Utility script to send emails from existing GCP impact reports.

Usage:
  python send_email.py path/to/report.md
  python send_email.py --list-reports
  python send_email.py --latest company_ticker
  python send_email.py --test-credentials
  python send_email.py --reauth
"""

import os
import sys
import glob
import json
import logging
import argparse
from datetime import datetime
from email_service import send_analysis_email, EmailService
import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def find_gcp_impact_reports(results_dir="results"):
    """Find all GCP impact reports in the results directory."""
    pattern = os.path.join(results_dir, "*_combined_gcp_impact.md")
    reports = glob.glob(pattern)
    
    # Sort by modification time (newest first)
    reports.sort(key=os.path.getmtime, reverse=True)
    
    return reports

def get_report_info(report_path):
    """Extract company and date information from report filename."""
    filename = os.path.basename(report_path)
    # Expected format: ticker_year_quarter_combined_gcp_impact.md or custom_timestamp_combined_gcp_impact.md
    parts = filename.split('_')
    
    if parts[0] == 'custom':
        return {
            'ticker': 'custom',
            'timestamp': parts[1] if len(parts) > 1 else 'unknown',
            'path': report_path,
            'modified': datetime.fromtimestamp(os.path.getmtime(report_path)).strftime('%Y-%m-%d %H:%M:%S')
        }
    else:
        return {
            'ticker': parts[0].upper() if parts else 'unknown',
            'year': parts[1] if len(parts) > 1 else 'unknown',
            'quarter': parts[2] if len(parts) > 2 else 'unknown',
            'path': report_path,
            'modified': datetime.fromtimestamp(os.path.getmtime(report_path)).strftime('%Y-%m-%d %H:%M:%S')
        }

def list_reports():
    """List all available GCP impact reports."""
    reports = find_gcp_impact_reports()
    
    if not reports:
        print("No GCP impact reports found in the results directory.")
        return
    
    print(f"\nFound {len(reports)} GCP impact report(s):\n")
    print(f"{'#':<3} {'TICKER':<8} {'PERIOD':<15} {'MODIFIED':<20} {'PATH'}")
    print("-" * 80)
    
    for idx, report_path in enumerate(reports):
        info = get_report_info(report_path)
        
        if info['ticker'] == 'custom':
            period = f"Custom ({info['timestamp']})"
        else:
            period = f"{info['quarter']} {info['year']}"
            
        print(f"{idx+1:<3} {info['ticker']:<8} {period:<15} {info['modified']:<20} {report_path}")

def get_latest_report_for_company(ticker):
    """Get the latest GCP impact report for a specific company."""
    reports = find_gcp_impact_reports()
    
    ticker = ticker.lower()
    company_reports = [r for r in reports if os.path.basename(r).startswith(f"{ticker}_")]
    
    if not company_reports:
        logging.error(f"No reports found for company ticker: {ticker}")
        return None
        
    return company_reports[0]  # Already sorted by modification time

def send_email_for_report(report_path, force_reauth=False):
    """
    Send an email with the content of the specified report.
    
    Args:
        report_path (str): Path to the report file
        force_reauth (bool): Whether to force reauthentication with Gmail API
    
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    if not os.path.exists(report_path):
        logging.error(f"Report not found: {report_path}")
        return False
    
    logging.info(f"Sending email for report: {report_path}")
    
    # Create an email service instance
    email_service = EmailService()
    
    # Authenticate with force_refresh if requested
    if email_service.authenticate(force_refresh=force_reauth):
        result = email_service.send_gcp_impact_email(report_path)
        
        if result['success']:
            recipients = result.get('recipients', [])
            cc = result.get('cc', [])
            all_recipients = recipients + cc
            logging.info(f"Email sent successfully to {', '.join(all_recipients)}")
            return True
        else:
            error = result.get('error', 'Unknown error')
            logging.error(f"Failed to send email: {error}")
            return False
    else:
        logging.error("Failed to authenticate with Gmail API")
        return False

def force_reauth():
    """
    Force reauthentication with Gmail API.
    
    When running on a headless server (like a Google Cloud VM), you should:
    1. SSH into the VM with port forwarding: 
       `gcloud compute ssh <instance-name> -- -L 8080:localhost:8080`
    2. Run this function with `python send_email.py --reauth`
    3. Open the displayed URL in your local browser to complete authentication
    """
    email_service = EmailService()
    
    if email_service.authenticate(force_refresh=True):
        logging.info("Successfully reauthenticated with Gmail API")
        return True
    else:
        logging.error("Failed to reauthenticate with Gmail API")
        return False

def test_credentials():
    """Test if the credentials file exists and is properly formatted."""
    # Create an email service instance
    email_service = EmailService()
    
    # Get the resolved credentials path
    credentials_path = email_service._resolve_env_reference(
        email_service.config.get("credentials_path", config.GMAIL_CREDENTIALS_PATH)
    )
    
    # Check if the file exists
    if not os.path.exists(credentials_path):
        logging.error(f"Credentials file not found: {credentials_path}")
        return False
    
    # Check if the file is a valid JSON
    try:
        with open(credentials_path, 'r') as f:
            credentials_data = json.load(f)
        
        # Check for required keys in the credentials file
        required_keys = ["installed", "web"]
        if not any(key in credentials_data for key in required_keys):
            logging.error(f"Credentials file is missing required data (installed or web section): {credentials_path}")
            return False
            
        logging.info(f"Credentials file is valid: {credentials_path}")
        
        # Log the contents of the installed section
        if "installed" in credentials_data:
            installed = credentials_data["installed"]
            if "client_id" in installed:
                client_id = installed["client_id"]
                # Mask the middle portion of the client ID for security
                masked_id = client_id[:8] + '*****' + client_id[-8:] if len(client_id) > 16 else client_id[:4] + '****'
                logging.info(f"Client ID: {masked_id}")
                
            if "redirect_uris" in installed:
                logging.info(f"Redirect URIs: {installed['redirect_uris']}")
                
        return True
    except json.JSONDecodeError:
        logging.error(f"Credentials file is not a valid JSON: {credentials_path}")
        return False
    except Exception as e:
        logging.error(f"Error reading credentials file: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Send emails from existing GCP impact reports')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('report_path', nargs='?', help='Path to the markdown report file')
    group.add_argument('--list-reports', action='store_true', help='List all available reports')
    group.add_argument('--latest', type=str, metavar='TICKER', help='Send email for latest report of the specified company')
    group.add_argument('--test-credentials', action='store_true', help='Test if the credentials file exists and is valid')
    group.add_argument('--reauth', action='store_true', help='Force reauthentication with Gmail API')
    
    parser.add_argument('--force-reauth', action='store_true', help='Force reauthentication when sending email')
    
    args = parser.parse_args()
    
    if args.list_reports:
        list_reports()
        return
        
    if args.test_credentials:
        test_credentials()
        return
        
    if args.reauth:
        success = force_reauth()
        print(f"\nReauthentication {'succeeded' if success else 'failed'}.")
        return
        
    if args.latest:
        report_path = get_latest_report_for_company(args.latest)
        if not report_path:
            print(f"\nNo reports found for company ticker: {args.latest}")
            return
    else:
        report_path = args.report_path
    
    if report_path:
        success = send_email_for_report(report_path, force_reauth=args.force_reauth)
        
        if success:
            print(f"\nEmail sent successfully for report: {os.path.basename(report_path)}")
        else:
            print(f"\nFailed to send email for report: {os.path.basename(report_path)}")
            print("Check the logs for more details.")
    else:
        print("\nNo report path specified. Use --list-reports to see available reports.")

if __name__ == "__main__":
    main() 