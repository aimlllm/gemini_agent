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
GMAIL_CREDENTIALS_PATH = os.getenv('GMAIL_CREDENTIALS_PATH', os.path.join(BASE_DIR, 'credentials.json'))

# API Keys
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Create necessary directories safely
def create_directory_if_not_exists(directory):
    """Create directory if it doesn't exist, handling permission errors gracefully."""
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
            logging.info(f"Created directory: {directory}")
        except (OSError, PermissionError) as e:
            logging.warning(f"Could not create directory {directory}: {e}")
            logging.warning("Using current directory as fallback")
            return False
    return True

# Create required directories
create_directory_if_not_exists(LOCAL_STORAGE_PATH)
create_directory_if_not_exists(RESULTS_DIR)
create_directory_if_not_exists(os.path.dirname(COMPANY_CONFIG_PATH)) 