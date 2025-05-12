#!/usr/bin/env python3
"""Configuration for the GCP Impact Analysis System."""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the directory containing this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Paths (ensure they're relative to the script location if not absolute)
LOCAL_STORAGE_PATH = os.getenv('LOCAL_STORAGE_PATH', os.path.join(BASE_DIR, 'downloads'))
RESULTS_DIR = os.getenv('RESULTS_DIR', os.path.join(BASE_DIR, 'results'))
COMPANY_CONFIG_PATH = os.getenv('COMPANY_CONFIG_PATH', os.path.join(BASE_DIR, 'config/company_config.json'))
EMAIL_CONFIG_PATH = os.getenv('EMAIL_CONFIG_PATH', os.path.join(BASE_DIR, 'config/email_config.json'))
GMAIL_CREDENTIALS_PATH = os.getenv('GMAIL_CREDENTIALS_PATH', os.path.join(BASE_DIR, 'config/token.pickle'))
GMAIL_CLIENT_SECRET_PATH = os.getenv('GMAIL_CLIENT_SECRET_PATH', os.path.join(BASE_DIR, 'config/credentials.json'))
PROMPT_CONFIG_PATH = os.getenv('PROMPT_CONFIG_PATH', os.path.join(BASE_DIR, 'config/prompt_config.txt'))

# API Keys
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Create directories if they don't exist
try:
    os.makedirs(LOCAL_STORAGE_PATH, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    logging.info(f"Storage directories created/verified: {LOCAL_STORAGE_PATH}, {RESULTS_DIR}")
except Exception as e:
    logging.warning(f"Could not create storage directories: {e}")
    # We'll handle fallbacks in the respective modules 