# Earnings Analysis System for Google Cloud Insights

A specialized system to analyze earnings call transcripts and financial reports from major tech companies using Google's Gemini API. The system focuses specifically on extracting Google Cloud Platform (GCP) relevant insights for executive decision-making, with capabilities to send analysis via email.

## Features

- Downloads earnings documents from verified authoritative sources
- Structured storage of earnings documents by company, year, and quarter
- Analyzes documents using Google Gemini 2.5 Pro with GCP-focused prompting
- Extracts competitor intelligence and strategic implications for Google Cloud
- Saves analysis in executive-friendly Markdown format
- Email delivery of analysis reports directly to stakeholders
- Simple command-line interface

## System Architecture

The system follows a modular architecture with the following components:

### 1. Configuration System
- `config/company_config.json`: Central JSON file storing all company information and document URLs
- Environment settings via `.env` file
- Support for environment variable references in JSON configs

### 2. Document Downloader
- Downloads documents based on information from the configuration
- Stores documents in a structured filesystem for analysis

### 3. Document Analyzer
- Analyzes documents using Google's Gemini API with GCP-focused prompting
- Extracts insights relevant to Google Cloud Platform strategy

### 4. Report Generator
- Formats analysis results into executive-friendly markdown
- Creates reports that can be directly included in emails

### 5. Email Service
- Sends analysis reports via email using Gmail API
- Supports HTML and plain text formatting
- OAuth authentication for secure access

## Setup

### 1. Clone the repository and install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

Edit the `.env` file with your Google Gemini API key and other settings:

```
GEMINI_API_KEY=your-api-key-here
LOCAL_STORAGE=true
LOCAL_STORAGE_PATH=downloads
COMPANY_CONFIG_PATH=config/company_config.json
EMAIL_CONFIG_PATH=config/email_config.json
GMAIL_CREDENTIALS_PATH=/path/to/your/credentials.json
```

### 3. Setup Gmail API (for email functionality)

Follow these step-by-step instructions to set up Gmail API access for sending emails:

#### Step 1: Create a Google Cloud Project
1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. In the top-right corner, click on your profile and make sure you're using the Google account you want to use for sending emails
3. Click on the project dropdown menu at the top of the page (next to "Google Cloud")
4. Click on "New Project" in the upper-right corner of the window that appears
5. Enter a name for your project (e.g., "GCP Impact Analysis")
6. Click "Create"
7. Wait for the project to be created (you'll be notified when it's ready)
8. Make sure your new project is selected in the dropdown at the top of the page

#### Step 2: Enable the Gmail API
1. In the left navigation menu, hover over "APIs & Services" and click "Library"
2. In the search bar at the top, type "Gmail API"
3. Click on "Gmail API" in the search results
4. Click the blue "Enable" button
5. Wait for the API to be enabled

#### Step 3: Configure OAuth Consent Screen
1. In the left navigation menu, click on "APIs & Services" > "OAuth consent screen"
2. Select "External" as the user type (unless you're in a Google Workspace organization, then you can select "Internal")
3. Click "Create"
4. Fill in the required fields:
   - App name: "GCP Impact Analysis"
   - User support email: Your email address
   - Developer contact information: Your email address
5. Click "Save and Continue"
6. On the "Scopes" page, click "Add or Remove Scopes"
7. Search for and select the scope: `https://mail.google.com/` 
   (This gives full access to Gmail, which is needed for sending emails)
8. Click "Update"
9. Click "Save and Continue"
10. On the "Test users" section:
    - Click "Add Users"
    - Enter your email address (the one you'll use to send emails)
    - Click "Add"
11. Click "Save and Continue"
12. Review the summary and click "Back to Dashboard"

#### Step 4: Create OAuth Client ID
1. In the left navigation menu, click on "APIs & Services" > "Credentials"
2. Click the "+ Create Credentials" button at the top of the page
3. Select "OAuth client ID" from the dropdown
4. Under "Application type," select "Desktop app"
5. Name: "GCP Impact Analysis Email Client"
6. Click "Create"
7. A popup will appear with your client ID and client secret
8. Click "Download JSON" to download your credentials file
9. Save this file to a secure location (you'll reference this in your `.env` file)

#### Step 5: Configure Email Settings
Create a `config/email_config.json` file with the following structure:

```json
{
  "enabled": true,
  "recipients": ["recipient1@example.com", "recipient2@example.com"],
  "cc": ["cc1@example.com", "cc2@example.com"],
  "email_subject_prefix": "[GCP Impact] ",
  "html_enabled": true,
  "credentials_path": ".env:GMAIL_CREDENTIALS_PATH",
  "token_path": "token.pickle",
  "sender_email": "your.email@gmail.com"
}
```

- `enabled`: Set to `true` to enable email sending, `false` to disable it
- `recipients`: List of primary email recipients
- `cc`: List of CC recipients (optional)
- `email_subject_prefix`: Prefix to add to email subjects
- `html_enabled`: Whether to send HTML-formatted emails
- `credentials_path`: Path to the OAuth credentials JSON file (can reference an environment variable)
- `token_path`: Path where the OAuth token will be stored
- `sender_email`: Fallback sender email address if profile access fails

#### Step 6: Update .env file with credentials path

Add the following to your `.env` file:

```
GMAIL_CREDENTIALS_PATH=/path/to/your/credentials.json
```

Replace `/path/to/your/credentials.json` with the actual path to the credentials file you downloaded.

## Usage

### Analyzing Latest Earnings by Ticker

```bash
python main.py --ticker AMZN
```

This will automatically:
1. Download the latest earnings documents for Amazon
2. Store them in a structured way in the local storage
3. Analyze them using Gemini API with a focus on GCP strategic implications
4. Save the results in executive-friendly Markdown format for email
5. Send the analysis by email if email functionality is enabled

### Using a Custom URL

If you want to analyze a specific earnings document that's not in our configuration:

```bash
python main.py --custom-url "https://example.com/earnings.pdf" --file-type earnings_release
```

### Listing Available Companies

```bash
python main.py --list-companies
```

### Sending Emails for Existing Reports

To send emails for reports that have already been generated, use the `send_email.py` utility:

```bash
# List available reports
python send_email.py --list-reports

# Send email for the latest report of a specific company
python send_email.py --latest TICKER

# Send email for a specific report
python send_email.py path/to/report.md

# Force reauthentication when sending
python send_email.py --latest TICKER --force-reauth

# Force reauthentication without sending an email
python send_email.py --reauth

# Test if your credentials file is valid
python send_email.py --test-credentials
```

### Command-Line Options

- `--ticker`: Company ticker symbol to analyze (e.g., AMZN, GOOGL, META)
- `--list-companies`: List all available companies and their latest quarters
- `--custom-url`: Analyze a custom URL not in the configuration
- `--file-type`: Type of file for custom URL (transcript or earnings_release)
- `--output-dir`: Directory to save analysis results (defaults to 'results')

## Available Companies

The system includes configuration for the following companies:

| Ticker | Company Name                         |
|--------|-------------------------------------|
| AMZN   | Amazon.com, Inc.                    |
| MSFT   | Microsoft Corporation               |
| META   | Meta Platforms, Inc.                |
| AMD    | Advanced Micro Devices, Inc.        |
| IBM    | International Business Machines Corp.|
| ORCL   | Oracle Corporation                  |
| BABA   | Alibaba Group                       |
| CRM    | Salesforce.com, Inc.                |
| SAP    | SAP SE                              |
| GOOGL  | Alphabet Inc. (Google)              |

## Email Authentication

The first time you use the email functionality, it will:

1. Open a browser window
2. Ask you to sign in to your Google account
3. Request permission to send emails
4. Redirect back to the application

After authenticating, your credentials will be saved so you don't need to authenticate again unless:
- The token expires
- You change the required scopes
- You explicitly request reauthentication using `--force-reauth` or `--reauth`

## Executive-Friendly Output

The system produces Markdown files specifically formatted for executive consumption. Each analysis includes:

1. **Header**: GCP impact focus, company name, ticker, and earnings period
2. **Executive Summary**: Quick overview of the analysis purpose
3. **Source Information**: Link to the original document and earnings date
4. **Analysis Content**: Structured Gemini analysis with GCP focus areas:
   - Financial Overview
   - Cloud Strategy and Competitive Position
   - Direct GCP Impacts
   - Indirect GCP Impacts
   - Customer and Partner Intelligence
   - Strategic Implications for GCP
5. **Footer**: Timestamp and disclaimer

Sample executive-friendly output structure:

```markdown
# GCP Impact Analysis: Amazon.com, Inc. (AMZN) - Q1 2025

> **EXECUTIVE SUMMARY**  
> This analysis examines Amazon's Q1 2025 earnings release with focus on implications for Google Cloud Platform's strategy and competitive position.
> Review the Strategic Implications section for recommended actions.

**Source:** [Earnings Release](https://ir.aboutamazon.com/files/doc_financials/2025/q1/AMZN-Q1-2025-Earnings-Release.pdf)  
**Earnings Date:** May 2, 2025  

## Financial Overview
...

## Cloud Strategy and Competitive Position
...

## Direct GCP Impacts
...

## Indirect GCP Impacts
...

## Customer and Partner Intelligence
...

## Strategic Implications for GCP
...

---
*Analysis generated on 2025-05-07 00:13:45 using Gemini 2.5 Pro*  
*This is an AI-generated analysis for Google Cloud executive team consumption only. Verify all information before making strategic decisions.*
```

## JSON Configuration Structure

The `config/company_config.json` file uses the following structure:

```json
{
  "companies": {
    "ticker": {
      "name": "Company Name",
      "ticker": "TICKER",
      "ir_site": "https://investor.company.com/",
      "releases": {
        "2025": {
          "Q1": {
            "date": "May 1, 2025",
            "time": "after-market close",
            "earnings_release": "https://investor.company.com/earnings.pdf",
            "call_transcript": "https://investor.company.com/transcript.pdf"
          },
          "Q2": {
            "expected_date": "August 1, 2025",
            "expected_time": "after-market close",
            "earnings_release": null,
            "call_transcript": null
          }
        }
      }
    }
  },
  "meta": {
    "last_updated": "2023-05-10T12:00:00Z",
    "version": "1.0.0"
  }
}
```

## Directory Structure

```
├── .env                  # Environment variables
├── requirements.txt      # Python dependencies
├── main.py               # Main script
├── config/               # Configuration files
│   ├── company_config.json  # Company information and document URLs
│   └── email_config.json    # Email configuration
├── config.py             # Configuration utilities
├── downloader.py         # Document downloader
├── analyzer.py           # Document analyzer using Gemini API
├── email_service.py      # Email service using Gmail API
├── send_email.py         # Utility to send emails for existing reports
├── token.pickle          # OAuth token storage (created on first email send)
├── downloads/            # Downloaded documents (created on first run)
│   ├── amzn/             # Documents for Amazon
│   │   └── 2025_Q1/      # Organized by quarter and year
│   ├── msft/             # Documents for Microsoft
│   └── ...               # Other companies
└── results/              # Analysis results (created on first run)
    └── amzn_2025_Q1_combined_gcp_impact.md  # GCP-focused markdown for email
```

## Troubleshooting

### Document Download Issues

Some companies restrict automated access to their earnings documents. If you encounter issues downloading documents, the system will provide instructions to manually download the documents from the company's investor relations site.

Common reasons for download failures:
1. Documents require login credentials or are behind a paywall
2. URLs have changed since the configuration was last updated
3. The company website has strict security measures against automated downloads

In these cases, you can:
1. Manually download the document from the company's IR site
2. Save it to the appropriate folder in the `downloads` directory
3. Use the custom URL option to analyze the local file

### Email Authentication Issues

#### "Request had insufficient authentication scopes"

If you see this error, you need to force reauthentication:

```bash
python send_email.py --reauth
```

This will delete the existing token and create a new one with the correct scopes.

#### "Credentials file not found"

Check that:
1. The path in your `.env` file is correct
2. The credentials file exists at that location
3. The file is a valid OAuth client ID JSON file from Google Cloud Console

#### "Error during OAuth flow"

If you encounter errors during the authentication process:
1. Ensure your Google account has not revoked access to the application
2. Check that you've completed all steps in the OAuth consent screen configuration
3. Verify that you've added yourself as a test user in the OAuth consent screen

#### Email Sending Fails

Check that:
1. Your internet connection is working
2. The email configuration in `config/email_config.json` is correct
3. The Gmail API is enabled in your Google Cloud project
4. You have granted the necessary permissions during the OAuth flow
5. Your OAuth token hasn't expired (use `--force-reauth` if needed)

## Future Enhancements

- Automated competitive tracking across cloud providers
- Historical trend analysis of cloud mentions across quarters
- Sentiment analysis on GCP references
- Auto-generated executive summaries of multiple earnings
- Dashboard integration for visualizing earnings insights
- API interface to allow other services to request analyses

## Security Considerations

1. The OAuth credentials file contains sensitive information. Keep it secure and do not commit it to version control.
2. The token file contains your OAuth refresh token. Keep it secure.
3. Add both credential files to your `.gitignore` to avoid committing them to version control.
4. The Gmail API will only have the permissions you explicitly grant during the OAuth process.
5. Keep your `.env` file secure as it contains sensitive API keys and configuration paths. 