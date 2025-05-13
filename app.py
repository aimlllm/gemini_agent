import os
import json
import logging
import subprocess
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import markdown

import config
from config_manager import ConfigManager
from downloader import EarningsDocDownloader
from analyzer import EarningsAnalyzer

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev_key_change_in_production')
app.config['UPLOAD_FOLDER'] = 'uploads'

# Ensure required directories exist
os.makedirs(config.RESULTS_DIR, exist_ok=True)
os.makedirs(os.path.dirname(config.COMPANY_CONFIG_PATH), exist_ok=True)
os.makedirs(os.path.dirname(config.EMAIL_CONFIG_PATH), exist_ok=True)
os.makedirs(os.path.dirname(config.PROMPT_CONFIG_PATH), exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize components
config_manager = ConfigManager()
analyzer = EarningsAnalyzer()
downloader = EarningsDocDownloader(config_manager)

@app.route('/')
def index():
    """Main dashboard page"""
    companies = config_manager.get_all_companies()
    return render_template('index.html', companies=companies)

@app.route('/run-analysis', methods=['POST'])
def run_analysis():
    """Run analysis for one or multiple companies"""
    # Handle both single and multi-company selection
    ticker = request.form.get('ticker')
    tickers = request.form.getlist('tickers')
    batch_process = request.form.get('batch_process') == 'on'
    
    # Check if we have any companies selected
    if not ticker and not tickers:
        flash("Please select at least one company", "error")
        return redirect(url_for('index'))
    
    # If single company mode
    if ticker and not tickers:
        return process_single_company(ticker)
    
    # If multi-company mode
    if tickers:
        if batch_process:
            return process_multiple_companies_batch(tickers)
        else:
            return process_multiple_companies_comparative(tickers)
    
    # Fallback
    flash("Invalid selection", "error")
    return redirect(url_for('index'))

def process_single_company(ticker):
    """Process a single company analysis"""
    try:
        company_info = config_manager.get_company(ticker)
        if not company_info:
            flash(f"Company ticker '{ticker}' not found", "error")
            return redirect(url_for('index'))
        
        year, quarter, release_data = config_manager.get_latest_release(ticker)
        if not release_data:
            flash(f"No release data found for {ticker}", "error")
            return redirect(url_for('index'))
        
        # Download documents
        download_result = downloader.download_latest_earnings(ticker)
        
        if not download_result or not download_result['files']:
            flash(f"No documents available for {ticker}. Please check IR site.", "error")
            return redirect(url_for('index'))
        
        # Analyze documents
        analysis = analyzer.analyze_earnings_documents(
            download_result['files'], 
            company_info['name'], 
            download_result['quarter'], 
            download_result['year']
        )
        
        # Save analysis
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{ticker}_{download_result['year']}_{download_result['quarter']}_{timestamp}.md"
        output_path = os.path.join(config.RESULTS_DIR, output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(analysis['analysis'] if isinstance(analysis, dict) and 'analysis' in analysis else str(analysis))
        
        flash(f"Analysis for {company_info['name']} has been completed and saved", "success")
        session['last_analysis'] = output_path
        
        return redirect(url_for('view_analysis', filename=output_filename))
    
    except Exception as e:
        logging.error(f"Error running analysis: {str(e)}")
        flash(f"Error running analysis: {str(e)}", "error")
        return redirect(url_for('index'))

def process_multiple_companies_batch(tickers):
    """Process multiple companies as separate analyses"""
    if not tickers:
        flash("No companies selected", "error")
        return redirect(url_for('index'))
    
    analysis_files = []
    error_companies = []
    successful_companies = []
    start_time = datetime.now()
    
    for ticker in tickers:
        try:
            company_info = config_manager.get_company(ticker)
            if not company_info:
                error_companies.append(f"{ticker} (not found)")
                continue
            
            year, quarter, release_data = config_manager.get_latest_release(ticker)
            if not release_data:
                error_companies.append(f"{ticker} (no release data)")
                continue
            
            # Download documents
            download_result = downloader.download_latest_earnings(ticker)
            
            if not download_result or not download_result['files']:
                error_companies.append(f"{ticker} (no documents)")
                continue
            
            # Analyze documents
            analysis = analyzer.analyze_earnings_documents(
                download_result['files'], 
                company_info['name'], 
                download_result['quarter'], 
                download_result['year']
            )
            
            # Save analysis
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"{ticker}_{download_result['year']}_{download_result['quarter']}_{timestamp}.md"
            output_path = os.path.join(config.RESULTS_DIR, output_filename)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(analysis['analysis'] if isinstance(analysis, dict) and 'analysis' in analysis else str(analysis))
            
            analysis_files.append(output_filename)
            successful_companies.append(company_info['name'])
            logging.info(f"Successfully analyzed {company_info['name']} ({ticker})")
        
        except Exception as e:
            logging.error(f"Error analyzing {ticker}: {str(e)}")
            error_companies.append(f"{ticker} (error: {str(e)[:50]}...)")
    
    # Calculate total processing time
    end_time = datetime.now()
    processing_time = (end_time - start_time).total_seconds()
    
    # Report results
    if analysis_files:
        if len(analysis_files) == 1:
            flash(f"Successfully analyzed {successful_companies[0]} in {processing_time:.1f} seconds", "success")
            return redirect(url_for('view_analysis', filename=analysis_files[0]))
        else:
            flash(f"Successfully analyzed {len(analysis_files)} companies in {processing_time:.1f} seconds: {', '.join(successful_companies)}", "success")
            if error_companies:
                flash(f"Failed to analyze {len(error_companies)} companies: {', '.join(error_companies)}", "warning")
            return redirect(url_for('analyses'))
    else:
        flash(f"Failed to analyze any companies: {', '.join(error_companies)}", "error")
        return redirect(url_for('index'))

def process_multiple_companies_comparative(tickers):
    """Process multiple companies as a single comparative analysis"""
    if not tickers:
        flash("No companies selected", "error")
        return redirect(url_for('index'))
    
    try:
        # Collect all company info and documents
        companies_data = []
        company_names = []
        failed_companies = []
        
        for ticker in tickers:
            try:
                company_info = config_manager.get_company(ticker)
                if not company_info:
                    failed_companies.append(f"{ticker} (company not found)")
                    continue
                    
                year, quarter, release_data = config_manager.get_latest_release(ticker)
                if not release_data:
                    failed_companies.append(f"{ticker} (no release data)")
                    continue
                    
                # Download documents
                download_result = downloader.download_latest_earnings(ticker)
                
                if not download_result or not download_result['files']:
                    failed_companies.append(f"{ticker} (no documents available)")
                    continue
                    
                companies_data.append({
                    'ticker': ticker,
                    'name': company_info['name'],
                    'files': download_result['files'],
                    'quarter': download_result['quarter'],
                    'year': download_result['year']
                })
                company_names.append(company_info['name'])
            except Exception as e:
                logging.error(f"Error processing company {ticker}: {str(e)}")
                failed_companies.append(f"{ticker} (error: {str(e)[:50]}...)")
        
        if not companies_data:
            if failed_companies:
                flash(f"Failed to process any companies: {', '.join(failed_companies)}", "error")
            else:
                flash("No valid companies found to analyze", "error")
            return redirect(url_for('index'))
        
        # Report partial failures but continue with available companies
        if failed_companies:
            flash(f"Some companies couldn't be processed: {', '.join(failed_companies)}", "warning")
            
        if len(companies_data) == 1:
            # If only one company is valid, switch to single company mode
            single_company = companies_data[0]
            flash(f"Only one company ({single_company['name']}) is available for analysis. Running single company analysis.", "warning")
            
            # Analyze documents for the single company
            analysis = analyzer.analyze_earnings_documents(
                single_company['files'], 
                single_company['name'], 
                single_company['quarter'], 
                single_company['year']
            )
            
            # Save analysis
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"{single_company['ticker']}_{single_company['year']}_{single_company['quarter']}_{timestamp}.md"
            output_path = os.path.join(config.RESULTS_DIR, output_filename)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(analysis['analysis'] if isinstance(analysis, dict) and 'analysis' in analysis else str(analysis))
            
            session['last_analysis'] = output_path
            return redirect(url_for('view_analysis', filename=output_filename))
            
        # Combine document sets for analysis
        combined_files = {}
        for company_data in companies_data:
            for file_type, file_path in company_data['files'].items():
                combined_key = f"{company_data['ticker']}_{file_type}"
                combined_files[combined_key] = file_path
        
        # Create a combined analysis name
        company_name_str = " vs. ".join(company_names)
        if len(company_name_str) > 100:  # Truncate if too long
            company_name_str = company_name_str[:97] + "..."
        
        # Use the quarter/year from the first company as reference
        reference_quarter = companies_data[0]['quarter']
        reference_year = companies_data[0]['year']
        
        # Let user know we're processing multiple companies
        logging.info(f"Running comparative analysis of {len(companies_data)} companies: {', '.join(company_names)}")
        
        # Analyze documents
        analysis = analyzer.analyze_earnings_documents(
            combined_files,
            company_name_str,
            reference_quarter,
            reference_year,
            is_comparative=True,
            companies=companies_data
        )
        
        # Save analysis
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        tickers_str = "_".join([c['ticker'] for c in companies_data])
        if len(tickers_str) > 50:  # Truncate if too long
            tickers_str = tickers_str[:47] + "..."
        
        output_filename = f"COMPARATIVE_{tickers_str}_{reference_year}_{reference_quarter}_{timestamp}.md"
        output_path = os.path.join(config.RESULTS_DIR, output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(analysis['analysis'] if isinstance(analysis, dict) and 'analysis' in analysis else str(analysis))
        
        companies_count = len(companies_data)
        flash(f"Comparative analysis of {companies_count} companies has been completed and saved", "success")
        session['last_analysis'] = output_path
        
        return redirect(url_for('view_analysis', filename=output_filename))
    
    except Exception as e:
        logging.error(f"Error running comparative analysis: {str(e)}")
        flash(f"Error running comparative analysis: {str(e)}", "error")
        return redirect(url_for('index'))

def render_markdown(content):
    """Convert markdown content to HTML for display"""
    extensions = ['extra', 'smarty', 'tables']
    return markdown.markdown(content, extensions=extensions)

@app.route('/view-analysis/<filename>')
def view_analysis(filename):
    """View a specific analysis file"""
    file_path = os.path.join(config.RESULTS_DIR, filename)
    
    if not os.path.exists(file_path):
        flash("Analysis file not found", "error")
        return redirect(url_for('analyses'))
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Convert markdown to HTML
        html_content = render_markdown(content)
        
        return render_template('view_analysis.html', 
                            content=html_content, 
                            raw_content=content,
                            filename=filename)
    except Exception as e:
        flash(f"Error reading file: {str(e)}", "error")
        return redirect(url_for('analyses'))

@app.route('/analyses')
def analyses():
    """List all available analyses"""
    files = []
    for filename in os.listdir(config.RESULTS_DIR):
        if filename.endswith('.md'):
            file_path = os.path.join(config.RESULTS_DIR, filename)
            files.append({
                'name': filename,
                'date': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S'),
                'size': os.path.getsize(file_path) // 1024  # KB
            })
    
    # Sort by date, newest first
    files.sort(key=lambda x: x['date'], reverse=True)
    
    return render_template('analyses.html', files=files)

@app.route('/send-email', methods=['POST'])
def send_email():
    """Send analysis email via command line"""
    filename = request.form.get('filename')
    
    if not filename:
        flash("No analysis file specified", "error")
        return redirect(url_for('analyses'))
    
    try:
        file_path = os.path.join(config.RESULTS_DIR, filename)
        
        # Use sys.executable to get the current Python interpreter path
        import sys
        python_executable = sys.executable
        
        # Use the full path to the Python interpreter
        result = subprocess.run(
            [python_executable, 'send_email.py', '--file', file_path],
            capture_output=True, 
            text=True
        )
        
        if result.returncode == 0:
            flash("Email sent successfully", "success")
        else:
            error_message = result.stderr.strip() or "Unknown error"
            logging.error(f"Email sending failed: {error_message}")
            flash(f"Error sending email: {error_message}", "error")
        
        return redirect(url_for('analyses'))
    
    except Exception as e:
        logging.error(f"Error sending email: {str(e)}")
        flash(f"Error sending email: {str(e)}", "error")
        return redirect(url_for('analyses'))

@app.route('/config/company', methods=['GET', 'POST'])
def edit_company_config():
    """Edit company configuration"""
    # Ensure config directory exists
    os.makedirs(os.path.dirname(config.COMPANY_CONFIG_PATH), exist_ok=True)
    
    if request.method == 'POST':
        try:
            config_data = request.form.get('config_data')
            # Validate JSON
            parsed = json.loads(config_data)
            
            with open(config.COMPANY_CONFIG_PATH, 'w', encoding='utf-8') as f:
                f.write(config_data)
            
            # Reload configuration
            config_manager.reload_config()
            
            flash("Company configuration updated successfully", "success")
            return redirect(url_for('edit_company_config'))
        
        except json.JSONDecodeError as e:
            flash(f"Invalid JSON: {str(e)}", "error")
        except Exception as e:
            flash(f"Error saving configuration: {str(e)}", "error")
    
    # Read current config or create default if doesn't exist
    try:
        if os.path.exists(config.COMPANY_CONFIG_PATH):
            with open(config.COMPANY_CONFIG_PATH, 'r', encoding='utf-8') as f:
                company_config = f.read()
        else:
            # Create default company config
            company_config = json.dumps({
                "companies": {
                    "example": {
                        "name": "Example Company",
                        "ticker": "EXMP",
                        "ir_site": "https://example.com/investor-relations",
                        "releases": {
                            "2025": {
                                "Q1": {
                                    "date": "April 30, 2025",
                                    "time": "after-market close",
                                    "earnings_release": "https://example.com/Q1-2025-earnings.pdf",
                                    "call_transcript": "https://example.com/Q1-2025-transcript.pdf"
                                }
                            }
                        }
                    }
                }
            }, indent=2)
            
            # Save default config
            os.makedirs(os.path.dirname(config.COMPANY_CONFIG_PATH), exist_ok=True)
            with open(config.COMPANY_CONFIG_PATH, 'w', encoding='utf-8') as f:
                f.write(company_config)
            
            flash("Created default company configuration. Please update with your company information.", "warning")
    except Exception as e:
        company_config = "{}"
        flash(f"Error reading configuration: {str(e)}", "error")
    
    return render_template('edit_config.html', 
                          config_type="Company", 
                          config_data=company_config,
                          config_path=config.COMPANY_CONFIG_PATH)

@app.route('/config/email', methods=['GET', 'POST'])
def edit_email_config():
    """Edit email configuration"""
    # Ensure config directory exists
    os.makedirs(os.path.dirname(config.EMAIL_CONFIG_PATH), exist_ok=True)
    
    if request.method == 'POST':
        try:
            config_data = request.form.get('config_data')
            # Validate JSON
            parsed = json.loads(config_data)
            
            with open(config.EMAIL_CONFIG_PATH, 'w', encoding='utf-8') as f:
                f.write(config_data)
            
            flash("Email configuration updated successfully", "success")
            return redirect(url_for('edit_email_config'))
        
        except json.JSONDecodeError as e:
            flash(f"Invalid JSON: {str(e)}", "error")
        except Exception as e:
            flash(f"Error saving configuration: {str(e)}", "error")
    
    # Read current config or create default if doesn't exist
    try:
        if os.path.exists(config.EMAIL_CONFIG_PATH):
            with open(config.EMAIL_CONFIG_PATH, 'r', encoding='utf-8') as f:
                email_config = f.read()
        else:
            # Create default email config
            email_config = json.dumps({
                "enabled": True,
                "recipients": ["user@example.com"],
                "cc": [],
                "credentials_path": ".env:GMAIL_CREDENTIALS_PATH",
                "token_path": "token.pickle",
                "email_subject_prefix": "GCP Impact Analysis: ",
                "html_enabled": True
            }, indent=2)
            
            # Save default config
            with open(config.EMAIL_CONFIG_PATH, 'w', encoding='utf-8') as f:
                f.write(email_config)
            
            flash("Created default email configuration. Please update with your recipients.", "warning")
    except Exception as e:
        email_config = "{}"
        flash(f"Error reading configuration: {str(e)}", "error")
    
    return render_template('edit_config.html', 
                          config_type="Email", 
                          config_data=email_config,
                          config_path=config.EMAIL_CONFIG_PATH)

@app.route('/config/prompt', methods=['GET', 'POST'])
def edit_prompt_config():
    """Edit prompt configuration"""
    # Ensure config directory exists
    os.makedirs(os.path.dirname(config.PROMPT_CONFIG_PATH), exist_ok=True)
    
    if request.method == 'POST':
        try:
            config_data = request.form.get('config_data')
            
            with open(config.PROMPT_CONFIG_PATH, 'w', encoding='utf-8') as f:
                f.write(config_data)
            
            flash("Prompt configuration updated successfully", "success")
            return redirect(url_for('edit_prompt_config'))
        
        except Exception as e:
            flash(f"Error saving configuration: {str(e)}", "error")
    
    # Read current config or create default if doesn't exist
    try:
        if os.path.exists(config.PROMPT_CONFIG_PATH):
            with open(config.PROMPT_CONFIG_PATH, 'r', encoding='utf-8') as f:
                prompt_config = f.read()
        else:
            # Create default prompt
            prompt_config = """You are a strategic analyst for Google Cloud Platform, analyzing {company_name}'s {quarter} {year} earnings documents.

Create an email-ready analysis that combines insights from all provided documents, focusing on:

## Financial Overview
- Key financial results with cloud market implications
- YoY growth rates in relevant areas (revenue, profit, R&D)

## Cloud Strategy and Competitive Position
- Current cloud strategy and market position
- Strategic direction changes or investments
- Competitive positioning against Google Cloud

## Technology and AI Investments
- Technology investments that might affect cloud adoption
- AI/ML initiatives that could complement or compete with GCP offerings
- Data center expansions or efficiency improvements
- Enterprise sales strategy changes relevant to cloud providers

## Customer and Partner Intelligence
- Notable customer wins or losses in cloud services
- Partner ecosystem developments relevant to cloud
- Changes in enterprise customer spending patterns

## Strategic Implications for Google/GCP
- Opportunities for Google Cloud based on these earnings documents
- Potential threats to Google Cloud's market position
- Recommended actions for GCP leadership

Format as clean, professional markdown suitable for immediate email distribution.
Be concise, data-driven, and actionable, focusing on strategic implications.
For each insight, specify the exact source (document type and location).

IMPORTANT: Do NOT include phrases like "Executive Summary" or "Here is an analysis of..." in your response.
Start directly with the content and ensure the analysis is self-contained and ready to be sent as is."""
            
            # Save default prompt
            with open(config.PROMPT_CONFIG_PATH, 'w', encoding='utf-8') as f:
                f.write(prompt_config)
            
            flash("Created default prompt configuration.", "warning")
    except Exception as e:
        prompt_config = ""
        flash(f"Error reading configuration: {str(e)}", "error")
    
    return render_template('edit_config.html', 
                          config_type="Prompt", 
                          config_data=prompt_config,
                          config_path=config.PROMPT_CONFIG_PATH)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=False) 