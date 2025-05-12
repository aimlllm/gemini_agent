import os
import logging
from datetime import datetime
import argparse

from config_manager import ConfigManager
from downloader import EarningsDocDownloader
from analyzer import EarningsAnalyzer
from email_service import send_analysis_email
import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def list_available_companies(config_manager):
    """Print a list of available companies with their tickers."""
    companies = config_manager.get_all_companies()
    
    print("\nAvailable companies:")
    print("-" * 70)
    print(f"{'TICKER':<8} {'COMPANY':<35} {'LATEST QUARTER':<15} {'YEAR'}")
    print("-" * 70)
    
    for ticker, info in companies.items():
        year, quarter, release_data = config_manager.get_latest_release(ticker)
        if year and quarter:
            print(f"{ticker.upper():<8} {info['name']:<35} {quarter:<15} {year}")
        else:
            print(f"{ticker.upper():<8} {info['name']:<35} {'N/A':<15} {'N/A'}")

def generate_email_markdown(analysis, config_manager):
    """
    Generate formatted markdown content for an email body from analysis results.
    
    Args:
        analysis (dict): Analysis results dict
        config_manager (ConfigManager): Configuration manager for company info
        
    Returns:
        str: Formatted markdown for email
    """
    company = analysis.get('company', 'Unknown Company')
    period = analysis.get('period', 'Unknown Period')
    ticker = analysis.get('ticker', '').upper()
    
    # Create a header with company info
    header = f"# GCP Impact Analysis: {company} ({ticker}) - {period}\n\n"
    
    # Add an executive summary box
    executive_summary = f"""
> **EXECUTIVE SUMMARY**  
> This analysis examines {company}'s {period} financial results with focus on implications for Google Cloud Platform's strategy and competitive position.
> Review the Strategic Implications section for recommended actions.
"""
    
    # Source document information - handle multiple document types
    source_info = ""
    if 'document_urls' in analysis:
        source_info = "**Source Documents:**  \n"
        for doc_type, url in analysis['document_urls'].items():
            display_type = doc_type.replace('_', ' ').title()
            source_info += f"- [{display_type}]({url})  \n"
    elif 'document_url' in analysis:
        document_type = analysis.get('document_type', 'earnings document').replace('_', ' ').title()
        source_info = f"**Source:** [{document_type}]({analysis['document_url']})  \n"
    
    # Get the earnings date from company config
    earnings_date = "Unknown"
    company_info = config_manager.get_company(ticker)
    if company_info:
        year, quarter, release_data = config_manager.get_latest_release(ticker)
        if release_data and "date" in release_data:
            earnings_date = release_data["date"]
    
    date_info = f"**Earnings Date:** {earnings_date}  \n\n"
    
    # The actual analysis content
    analysis_content = analysis.get('analysis', 'No analysis available.')
    
    # Add a footer with generation timestamp and disclaimer
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    footer = f"\n\n---\n*Analysis generated on {timestamp} using Gemini 2.5 Pro*  \n"
    footer += "*This is an AI-generated analysis for Google Cloud executive team consumption only. Verify all information before making strategic decisions.*"
    
    # Combine all parts
    email_content = header + executive_summary + source_info + date_info + analysis_content + footer
    
    return email_content

def main():
    parser = argparse.ArgumentParser(description='Analyze earnings documents for tech companies')
    parser.add_argument('--ticker', type=str, help='Company ticker to analyze (e.g., AMZN, GOOGL)')
    parser.add_argument('--list-companies', action='store_true', help='List all available companies')
    parser.add_argument('--custom-url', type=str, help='Custom URL to analyze (if not using pre-configured URLs)')
    parser.add_argument('--file-type', choices=['transcript', 'earnings_release'], 
                      help='Type of file for custom URL (required if --custom-url is provided)')
    parser.add_argument('--output-dir', type=str, default='results',
                        help='Directory to save analysis results')
    parser.add_argument('--config-file', type=str, default=None,
                        help=f'Path to company configuration JSON file (default: {config.COMPANY_CONFIG_PATH})')
    parser.add_argument('--skip-email', action='store_true',
                        help='Skip sending email (useful when email credentials are not available)')
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    try:
        if not os.path.exists(args.output_dir):
            os.makedirs(args.output_dir)
    except (OSError, PermissionError) as e:
        logging.warning(f"Could not create output directory {args.output_dir}: {e}")
        args.output_dir = os.path.join(os.getcwd(), 'results')
        logging.warning(f"Using fallback output directory: {args.output_dir}")
        try:
            if not os.path.exists(args.output_dir):
                os.makedirs(args.output_dir)
        except (OSError, PermissionError) as e:
            logging.error(f"Could not create fallback output directory: {e}")
            logging.error("Analysis will be performed but results cannot be saved")
    
    # Initialize configuration manager
    config_manager = ConfigManager(args.config_file)
    
    # Initialize downloader and analyzer
    downloader = EarningsDocDownloader(config_manager)
    analyzer = EarningsAnalyzer()
    
    # List companies if requested
    if args.list_companies:
        list_available_companies(config_manager)
        return
    
    # Check if ticker is provided
    if not args.ticker and not args.custom_url:
        logging.error("Please provide either --ticker or --custom-url.")
        logging.info("For a list of available companies, use --list-companies")
        return
    
    # Process ticker-based analysis
    if args.ticker:
        ticker = args.ticker.lower()
        
        company_info = config_manager.get_company(ticker)
        if not company_info:
            logging.error(f"Error: Ticker '{args.ticker}' not found in configuration.")
            logging.info("For a list of available companies, use --list-companies")
            return
        
        year, quarter, release_data = config_manager.get_latest_release(ticker)
        if not release_data:
            logging.error(f"No release data found for {ticker}")
            return
        
        logging.info(f"\nAnalyzing latest earnings for {company_info['name']} ({company_info['ticker']})")
        logging.info(f"Quarter: {quarter} {year}")
        if "date" in release_data:
            logging.info(f"Release Date: {release_data['date']}")
        
        # Download latest earnings documents
        download_result = downloader.download_latest_earnings(ticker)
        
        if not download_result or not download_result['files']:
            logging.error(f"\nNo documents available for automatic download for {company_info['ticker']}.")
            logging.info(f"Please check the investor relations site: {company_info['ir_site']}")
            return
        
        # Use the combined document analyzer if we have multiple documents
        logging.info(f"Creating combined analysis from all available documents...")
        analysis = analyzer.analyze_earnings_documents(
            download_result['files'],
            company_info['name'],
            download_result['quarter'],
            download_result['year']
        )
        
        # Add ticker for email generation
        analysis['ticker'] = company_info['ticker']
    
    # Process custom URL analysis
    elif args.custom_url:
        if not args.file_type:
            logging.error("Error: When using --custom-url, you must specify --file-type")
            return
        
        logging.info(f"\nDownloading document from custom URL: {args.custom_url}")
        
        # For custom URLs, create a generic identifier
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = downloader.download_file(
            args.custom_url,
            "custom",
            "custom",
            timestamp,
            args.file_type
        )
        
        if not file_path:
            logging.error("Error downloading from custom URL.")
            return
        
        logging.info(f"\nAnalyzing {args.file_type} from custom URL...")
        
        # For custom URLs, analyze as a single document
        analysis = analyzer.analyze_document(
            file_path,
            "Custom Company",
            "Custom",
            timestamp,
            args.file_type
        )
        
        # Add document information to analysis
        analysis['document_type'] = args.file_type
        analysis['document_url'] = args.custom_url
    
    # Save analysis to output directory
    if analysis:
        # Create a unique identifier for the analysis files
        if args.ticker:
            identifier = f"{args.ticker.lower()}_{download_result['year']}_{download_result['quarter']}"
        else:
            identifier = f"custom_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Generate email-friendly markdown
        email_markdown = generate_email_markdown(analysis, config_manager)
        
        # Save as markdown file
        analysis_filename = f"{identifier}_combined_gcp_impact.md"
        analysis_path = os.path.join(args.output_dir, analysis_filename)
        
        try:
            with open(analysis_path, 'w') as f:
                f.write(email_markdown)
            
            logging.info(f"GCP impact analysis saved to {analysis_path} (email-friendly format)")
        except (OSError, PermissionError) as e:
            logging.error(f"Could not save analysis to {analysis_path}: {e}")
            print("\nAnalysis Results:")
            print("=" * 80)
            print(email_markdown)
            print("=" * 80)
        
        # Send email using the email configuration (if not skipped)
        if not args.skip_email:
            try:
                # Check if email_config.json exists
                if os.path.exists(config.EMAIL_CONFIG_PATH):
                    logging.info(f"Sending analysis via email (configured in {config.EMAIL_CONFIG_PATH})")
                    try:
                        email_result = send_analysis_email(analysis_path)
                        
                        if email_result.get('success', False):
                            recipients = email_result.get('recipients', [])
                            cc = email_result.get('cc', [])
                            all_recipients = recipients + cc
                            logging.info(f"Email sent successfully to {', '.join(all_recipients)}")
                        else:
                            error = email_result.get('error', 'Unknown error')
                            logging.info(f"Email not sent: {error}")
                    except Exception as e:
                        logging.error(f"Error during email sending: {str(e)}")
                        logging.info("Email functionality skipped - you can still view the analysis file")
                else:
                    logging.info(f"Email not sent ({config.EMAIL_CONFIG_PATH} not found)")
            except Exception as e:
                logging.error(f"Error in email configuration: {str(e)}")
                logging.info("Analysis completed but email functionality was skipped")
        else:
            logging.info("Email sending skipped (--skip-email flag used)")

if __name__ == "__main__":
    main() 