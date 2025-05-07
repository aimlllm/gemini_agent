#!/usr/bin/env python3
"""Configuration for the GCP Impact Analysis System."""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Paths
LOCAL_STORAGE_PATH = os.getenv('LOCAL_STORAGE_PATH', 'downloads')
RESULTS_DIR = os.getenv('RESULTS_DIR', 'results')
COMPANY_CONFIG_PATH = os.getenv('COMPANY_CONFIG_PATH', 'config/company_config.json')
EMAIL_CONFIG_PATH = os.getenv('EMAIL_CONFIG_PATH', 'config/email_config.json')
GMAIL_CREDENTIALS_PATH = os.getenv('GMAIL_CREDENTIALS_PATH', 'credentials.json')

# API Keys
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Create necessary directories
if not os.path.exists(LOCAL_STORAGE_PATH):
    os.makedirs(LOCAL_STORAGE_PATH)

if not os.path.exists(RESULTS_DIR):
    os.makedirs(RESULTS_DIR)
    
if not os.path.exists(os.path.dirname(COMPANY_CONFIG_PATH)):
    os.makedirs(os.path.dirname(COMPANY_CONFIG_PATH)) 