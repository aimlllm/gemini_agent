#!/usr/bin/env python3
"""
Utility script to send emails from existing GCP impact reports.

Usage:
  python send_email.py path/to/report.md
  python send_email.py --file path/to/report.md  (explicit file path)
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
    pattern = os.path.join(results_dir, "*.md")
    reports = glob.glob(pattern)
    
    # Sort by modification time (newest first)
    reports.sort(key=os.path.getmtime, reverse=True)
    
    return reports

def get_report_info(report_path):
    """Extract company and date information from report filename."""
    filename = os.path.basename(report_path)
    # Parse various filename formats
    parts = filename.split('_')
    
    if filename.startswith('COMPARATIVE_'):
        return {
            'type': 'comparative',
            'tickers': parts[1] if len(parts) > 1 else 'unknown',
            'year': parts[2] if len(parts) > 2 else 'unknown',
            'quarter': parts[3] if len(parts) > 3 else 'unknown',
            'path': report_path,
            'modified': datetime.fromtimestamp(os.path.getmtime(report_path)).strftime('%Y-%m-%d %H:%M:%S')
        }
    elif parts[0] == 'custom':
        return {
            'type': 'custom',
            'ticker': 'custom',
            'timestamp': parts[1] if len(parts) > 1 else 'unknown',
            'path': report_path,
            'modified': datetime.fromtimestamp(os.path.getmtime(report_path)).strftime('%Y-%m-%d %H:%M:%S')
        }
    else:
        return {
            'type': 'single',
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
        print("No analysis reports found in the results directory.")
        return
    
    print(f"\nFound {len(reports)} analysis report(s):\n")
    print(f"{'#':<3} {'TYPE':<12} {'COMPANY/TICKER':<20} {'PERIOD':<15} {'MODIFIED':<20} {'PATH'}")
    print("-" * 100)
    
    for idx, report_path in enumerate(reports):
        info = get_report_info(report_path)
        
        if info.get('type') == 'comparative':
            report_type = "Comparative"
            company = info.get('tickers', 'multiple')[:18]
            period = f"{info.get('quarter', '?')} {info.get('year', '?')}"
        elif info.get('type') == 'custom' or info.get('ticker') == 'custom':
            report_type = "Custom"
            company = "Custom Report"
            period = f"Custom ({info.get('timestamp', '?')})"
        else:
            report_type = "Single"
            company = info.get('ticker', 'unknown')
            period = f"{info.get('quarter', '?')} {info.get('year', '?')}"
            
        print(f"{idx+1:<3} {report_type:<12} {company:<20} {period:<15} {info['modified']:<20} {report_path}")

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
        error_msg = f"Report file not found: {report_path}"
        logging.error(error_msg)
        print(error_msg, file=sys.stderr)
        return False
    
    logging.info(f"Sending email for report: {report_path}")
    
    try:
    # Create an email service instance
    email_service = EmailService()
    
    # Authenticate with force_refresh if requested
    if email_service.authenticate(force_refresh=force_reauth):
        result = email_service.send_gcp_impact_email(report_path)
        
        if result['success']:
            recipients = result.get('recipients', [])
            cc = result.get('cc', [])
            all_recipients = recipients + cc
                success_msg = f"Email sent successfully to {', '.join(all_recipients)}"
                logging.info(success_msg)
            return True
        else:
            error = result.get('error', 'Unknown error')
                error_msg = f"Failed to send email: {error}"
                logging.error(error_msg)
                print(error_msg, file=sys.stderr)
                return False
        else:
            error_msg = "Failed to authenticate with Gmail API"
            logging.error(error_msg)
            print(error_msg, file=sys.stderr)
            return False
            
    except Exception as e:
        error_msg = f"Error sending email: {str(e)}"
        logging.error(error_msg)
        print(error_msg, file=sys.stderr)
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
    parser = argparse.ArgumentParser(description='Send emails from analysis reports')
    
    # Create a group for report specification options
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('report_path', nargs='?', help='Path to the markdown report file')
    group.add_argument('--file', type=str, metavar='FILE', help='Explicit path to the markdown report file')
    group.add_argument('--list-reports', action='store_true', help='List all available reports')
    group.add_argument('--latest', type=str, metavar='TICKER', help='Send email for latest report of the specified company')
    group.add_argument('--test-credentials', action='store_true', help='Test if the credentials file exists and is valid')
    group.add_argument('--reauth', action='store_true', help='Force reauthentication with Gmail API')
    
    # Additional options
    parser.add_argument('--force-reauth', action='store_true', help='Force reauthentication when sending email')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    
    # Parse the arguments
    args = parser.parse_args()
    
    # Set more verbose logging if requested
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # List all reports
    if args.list_reports:
        list_reports()
        return 0
        
    # Test credentials
    if args.test_credentials:
        if test_credentials():
            print("\nCredentials test passed successfully.")
            return 0
        else:
            print("\nCredentials test failed. Check the logs for details.")
            return 1
    
    # Force reauthentication
    if args.reauth:
        success = force_reauth()
        print(f"\nReauthentication {'succeeded' if success else 'failed'}.")
        return 0 if success else 1
        
    # Send email for latest report
    if args.latest:
        report_path = get_latest_report_for_company(args.latest)
        if not report_path:
            print(f"\nNo reports found for company ticker: {args.latest}")
            return 1
    # Send email for specified file
    elif args.file:
        report_path = args.file
    # Send email for specified report path
    else:
        report_path = args.report_path
    
    # Validate report path
    if not report_path:
        print("\nNo report path specified. Use --list-reports to see available reports.")
        return 1
    
    # Check if the file exists
    if not os.path.exists(report_path):
        print(f"\nError: Report file not found: {report_path}")
        return 1
    
    # Send the email
        success = send_email_for_report(report_path, force_reauth=args.force_reauth)
        
        if success:
            print(f"\nEmail sent successfully for report: {os.path.basename(report_path)}")
        return 0
        else:
            print(f"\nFailed to send email for report: {os.path.basename(report_path)}")
            print("Check the logs for more details.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 