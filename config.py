import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Storage configuration
LOCAL_STORAGE = os.getenv('LOCAL_STORAGE', 'true').lower() == 'true'
LOCAL_STORAGE_PATH = os.getenv('LOCAL_STORAGE_PATH', 'downloads')

# Configuration file paths
COMPANY_CONFIG_PATH = os.getenv('COMPANY_CONFIG_PATH', 'config/company_config.json')
EMAIL_CONFIG_PATH = os.getenv('EMAIL_CONFIG_PATH', 'config/email_config.json')

# Gmail API credentials
GMAIL_CREDENTIALS_PATH = os.getenv('GMAIL_CREDENTIALS_PATH', 'credentials.json')
GMAIL_TOKEN_PATH = os.getenv('GMAIL_TOKEN_PATH', 'token.pickle')

# Create necessary directories if they don't exist
if LOCAL_STORAGE and not os.path.exists(LOCAL_STORAGE_PATH):
    os.makedirs(LOCAL_STORAGE_PATH)
    
if not os.path.exists(os.path.dirname(COMPANY_CONFIG_PATH)):
    os.makedirs(os.path.dirname(COMPANY_CONFIG_PATH)) 