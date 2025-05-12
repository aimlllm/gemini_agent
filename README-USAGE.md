# Downloading and Analyzing Latest Earnings Documents

This document provides instructions for downloading and analyzing the latest earnings documents for companies configured in the system.

## Command Line Usage

The system is designed to always use the most recent earnings data available in the `company_config.json` file. When you specify a ticker symbol, the system will:

1. Find the most recent year and quarter with an actual release date
2. Download both the earnings release and transcript (if available)
3. Analyze the documents with Gemini API
4. Generate an analysis report

### Basic Usage

To download and analyze the latest earnings documents for a company:

```bash
python main.py --ticker SYMBOL
```

Replace `SYMBOL` with the ticker symbol (e.g., AMZN, MSFT, META, etc.). The command is case-insensitive.

Examples:
```bash
# Analyze Amazon's latest earnings
python main.py --ticker AMZN

# Analyze Microsoft's latest earnings
python main.py --ticker MSFT

# Analyze Meta's latest earnings
python main.py --ticker META
```

### Viewing Available Companies

To see a list of all available companies and their latest quarters:

```bash
python main.py --list-companies
```

This will display a table showing all companies in the configuration, along with their most recent earnings period.

### How the Latest Documents Are Determined

The system uses the following algorithm to determine the latest earnings documents:

1. Sorts all years in reverse order to find the most recent year
2. Within the most recent year, finds the most recent quarter with an actual release date (not just an expected date)
3. Uses the documents linked in that quarter's configuration

### Custom URLs

If you want to analyze a document not in the configuration:

```bash
python main.py --custom-url "https://example.com/earnings.pdf" --file-type earnings_release
```

Valid file types are:
- `earnings_release` - For earnings press releases
- `transcript` - For earnings call transcripts

## Technical Details

The system uses these key components to handle latest documents:

1. **ConfigManager.get_latest_release(ticker)** - Determines the most recent earnings period for a company
2. **EarningsDocDownloader.download_latest_earnings(ticker)** - Downloads the documents for the latest period
3. **EarningsAnalyzer.analyze_earnings_documents(documents, company_name, quarter, year)** - Analyzes the documents

## Troubleshooting

If you encounter issues downloading documents:

1. **Access Denied (403)** - Some documents (especially on SeekingAlpha) require authentication
   - Alternative: Try downloading manually and placing in the correct downloads directory
   - Format: `downloads/{ticker}/{year}_{quarter}/{filename}`

2. **Missing Documents** - If a document URL is missing in the configuration:
   - Edit `config/company_config.json` to add the missing URLs

3. **Document Not Found (404)** - If a URL no longer works:
   - Check the company's investor relations site for updated links
   - Update `config/company_config.json` with new URLs

4. **Permission Errors** - If you see "Read-only file system" or permission errors:
   - Make sure the `downloads` and `results` directories are writable
   - You can customize storage paths using environment variables:
     ```
     LOCAL_STORAGE_PATH=/path/to/writable/location/downloads
     RESULTS_DIR=/path/to/writable/location/results
     ```
   - Or create a `.env` file in the project root with these variables

5. **Alternative Sources for Transcripts** - If you can't access SeekingAlpha transcripts:
   - Check the company's Investor Relations website for official transcripts
   - Look for transcripts on free financial sites like Yahoo Finance, Motley Fool, or AlphaStreet
   - For companies with good IR sites, update the transcript URL in `config/company_config.json` 