# Partner S&O Earnings Reader Web Interface

This web interface provides a user-friendly way to manage your Partner S&O Earnings Reader system.

## Features

- **Dashboard**: Run analyses for companies configured in your system
  - Single company analysis
  - Multi-company comparative analysis
  - Batch processing of multiple companies
- **Analysis Management**: View, manage, and send analysis results via email
- **Configuration Editor**: Easily edit your configuration files:
  - Company configuration (earnings releases, document URLs)
  - Email settings (recipients, subject prefix)
  - Prompt template (customize the prompt sent to Gemini API)

## Installation

1. Make sure you have installed all the requirements:

```bash
pip install -r requirements.txt
```

2. Run the web application:

```bash
python app.py
```

The server will start on http://localhost:8080 by default.

## Deployment Options

### Local Development

For local development or quick testing, you can run the app directly:

```bash
python app.py
```

Or use the included script:

```bash
./run_web.sh
```

### Cloud Deployment (Google Cloud VM)

For running on a cloud VM as a persistent service:

1. Use our automatic setup script:

```bash
./setup_cloud_service.sh
```

This will:
- Detect your virtual environment
- Set up a systemd service
- Configure auto-restart and boot startup
- Show you how to manage the application

2. After setup, manage the service using:

```bash
# Start the application
sudo systemctl start gemini-web

# Stop the application
sudo systemctl stop gemini-web

# Restart after code changes
sudo systemctl restart gemini-web

# Check if it's running
sudo systemctl status gemini-web
```

For detailed instructions, see [README-CLOUD-SETUP.md](README-CLOUD-SETUP.md).

## Usage

### Running Analyses

#### Single Company Analysis
1. From the dashboard, select a company from the dropdown
2. Click "Run Analysis" to download the latest earnings documents and analyze them
3. The analysis will be saved and you'll be redirected to view the results

#### Multi-Company Analysis
1. Toggle the "Multi-select" switch in the Run Analysis card
2. Select two or more companies using the checkboxes
3. Choose one of these analysis modes:
   - **Comparative Analysis**: Creates a single report comparing all selected companies (default)
   - **Batch Processing**: Analyzes each company separately, creating multiple reports

The system will process the companies and redirect you to view the results.

### Viewing Previous Analyses

1. Go to the "Analyses" page from the navigation menu
2. Browse the list of previous analyses with creation dates
3. Click "View" to see the full content of an analysis
4. Use "Send Email" to distribute the analysis via email

### Managing Configurations

1. Select the configuration type from the navigation menu:
   - **Company Config**: Add/edit companies and their earnings releases
   - **Email Config**: Set up email recipients and delivery options
   - **Prompt Config**: Customize the prompt template for Gemini API

2. Make your changes in the editor
3. Click "Save Changes" to update the configuration

## Environment Variables

You can configure the application using the following environment variables:

- `PORT`: Web server port (default: 8080)
- `FLASK_SECRET_KEY`: Secret key for Flask sessions (important for production)
- `GEMINI_API_KEY`: Your Gemini API key

## Deployment

For production deployment:

1. Set a strong `FLASK_SECRET_KEY`
2. Configure a reverse proxy (Nginx, Apache) in front of the application
3. Use a WSGI server like Gunicorn:

```bash
gunicorn -w 4 -b 0.0.0.0:8080 app:app
```

## Security Notes

- This interface is designed for internal use only
- Implement proper authentication if deploying in a shared environment
- Secure your API keys and credentials 