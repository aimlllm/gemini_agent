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
    """Run analysis for a specific company"""
    ticker = request.form.get('ticker')
    
    if not ticker:
        flash("Please select a company ticker", "error")
        return redirect(url_for('index'))
    
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
        result = subprocess.run(
            ['python', 'send_email.py', '--file', file_path],
            capture_output=True, 
            text=True
        )
        
        if result.returncode == 0:
            flash("Email sent successfully", "success")
        else:
            flash(f"Error sending email: {result.stderr}", "error")
        
        return redirect(url_for('analyses'))
    
    except Exception as e:
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