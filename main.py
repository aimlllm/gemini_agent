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

def generate_email_markdown(result, config_manager=None):
    """
    Generate email-friendly markdown from analysis results.
    
    Args:
        result (dict): Analysis result
        config_manager (ConfigManager, optional): ConfigManager instance
        
    Returns:
        str: Email-friendly markdown
    """
    if 'error' in result:
        return f"# ERROR: {result['error']}\n\nFailed to analyze {result['company']} earnings."
    
    # Get company info
    company = result['company']
    ticker = result['ticker']
    quarter = result['quarter'] if 'quarter' in result else 'Unknown Period'
    year = result['year'] if 'year' in result else ''
    period = f"{quarter} {year}".strip()
    
    # Format the output
    email_md = f"# GCP Impact Analysis: {company} ({ticker}) - {period}\n\n\n"
    email_md += f"> **EXECUTIVE SUMMARY**  \n"
    email_md += f"> This analysis examines {company}'s {period} financial results with focus on implications for Google Cloud Platform's strategy and competitive position.\n"
    email_md += f"> Review the Strategic Implications section for recommended actions.\n"
    
    # Add release date if available
    if 'release_date' in result:
        email_md += f"**Earnings Date:** {result['release_date']}  \n\n"
    
    # Add the content
    if 'content' in result and result['content']:
        content = result['content']
        email_md += content if not content.startswith('Error:') else f"**ERROR:** {content}"
    else:
        email_md += "No analysis available.\n"
    
    # Add footer
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    email_md += f"\n\n---\n*Analysis generated on {current_time} using Gemini 2.5 Pro*  \n"
    email_md += "*This is an AI-generated analysis for Google Cloud executive team consumption only. Verify all information before making strategic decisions.*"
    
    return email_md

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
        
        # Provide info about which documents we have
        available_docs = list(download_result['files'].keys())
        logging.info(f"Available documents for analysis: {', '.join(available_docs)}")
        
        # Add warning if transcript is missing (common with SeekingAlpha)
        if 'call_transcript' not in available_docs:
            logging.warning("Call transcript is not available. Analysis will be based only on earnings release.")
            if 'call_transcript' in release_data and 'seekingalpha.com' in release_data['call_transcript']:
                logging.warning("SeekingAlpha transcripts require a subscription. Consider finding an alternative source.")
        
        # Analyze documents
        analysis = analyzer.analyze_earnings_documents(
            download_result['files'], company_info['name'], download_result['quarter'], download_result['year']
        )
        
        # Format the result
        result = {
            'content': analysis['analysis'] if isinstance(analysis, dict) and 'analysis' in analysis else analysis,
            'ticker': company_info['ticker'],
            'company': company_info['name'],
            'quarter': download_result['quarter'],
            'year': download_result['year'],
            'documents': download_result['files'],
            'release_date': release_data.get('date', 'Unknown')
        }
        
        # Save the analysis
        output_path = os.path.join(
            args.output_dir,
            f"{company_info['ticker'].lower()}_{download_result['year']}_{download_result['quarter']}_combined_gcp_impact.md"
        )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result['content'])
        logging.info(f"Analysis saved to {output_path}")
        
        # Add ticker for email generation
        result['ticker'] = company_info['ticker']
    
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
        documents = {args.file_type: {'path': file_path, 'url': args.custom_url}}
        analysis = analyzer.analyze_earnings_documents(
            documents,
            "Custom Company",
            "Custom",
            timestamp
        )
        
        # Format the result
        result = {
            'content': analysis['analysis'] if isinstance(analysis, dict) and 'analysis' in analysis else analysis,
            'ticker': 'custom',
            'company': 'Custom Company',
            'quarter': 'Custom',
            'year': timestamp,
            'documents': [file_path]
        }
        
        # Save the analysis
        output_path = os.path.join(
            args.output_dir,
            f"custom_{datetime.now().strftime('%Y%m%d_%H%M%S')}_combined_gcp_impact.md"
        )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result['content'])
        logging.info(f"Analysis saved to {output_path}")
    
    # Save analysis to output directory
    if result:
        # Generate email-friendly markdown
        email_markdown = generate_email_markdown(result, config_manager)
        
        # Save as markdown file
        analysis_filename = f"{result['ticker']}_{result['year']}_{result['quarter']}_combined_gcp_impact.md"
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