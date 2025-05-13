#!/bin/bash
# Setup script for Gemini Earnings Analyzer web interface
# This will set up a systemd service to run the application

# Text formatting
BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BOLD}Gemini Earnings Analyzer - Cloud Setup${NC}"
echo "This script will set up your application to run as a system service."
echo

# Get the current user
CURRENT_USER=$(whoami)

# Get the current directory
CURRENT_DIR=$(pwd)

# Get Python path from virtual environment if active
if [[ -n "$VIRTUAL_ENV" ]]; then
    PYTHON_PATH="$VIRTUAL_ENV/bin/python"
    echo -e "${GREEN}Using Python from virtual environment: $PYTHON_PATH${NC}"
else
    # Try to find a virtualenv in the current directory
    if [[ -d "venv" && -f "venv/bin/python" ]]; then
        PYTHON_PATH="$CURRENT_DIR/venv/bin/python"
        echo -e "${GREEN}Found Python in local venv: $PYTHON_PATH${NC}"
    elif [[ -d "env" && -f "env/bin/python" ]]; then
        PYTHON_PATH="$CURRENT_DIR/env/bin/python"
        echo -e "${GREEN}Found Python in local env: $PYTHON_PATH${NC}"
    else
        # Use system Python as fallback
        PYTHON_PATH=$(which python3)
        echo -e "${YELLOW}Using system Python: $PYTHON_PATH${NC}"
        echo -e "${YELLOW}Note: It's recommended to use a virtual environment${NC}"
    fi
fi

# Ask for port
read -p "Enter the port number for the web interface [8080]: " PORT
PORT=${PORT:-8080}

# Ask for secret key
read -p "Enter a secret key for Flask (or press Enter to generate one): " SECRET_KEY
if [[ -z "$SECRET_KEY" ]]; then
    SECRET_KEY=$(openssl rand -hex 24)
    echo -e "${GREEN}Generated secret key: $SECRET_KEY${NC}"
fi

# Ask for API key if needed
read -p "Enter your Gemini API key (leave blank if set elsewhere): " API_KEY

# Create the service file content
SERVICE_CONTENT="[Unit]
Description=Gemini Earnings Analyzer Web Interface
After=network.target

[Service]
User=$CURRENT_USER
WorkingDirectory=$CURRENT_DIR
ExecStart=$PYTHON_PATH $CURRENT_DIR/app.py
Restart=always
RestartSec=10
Environment=\"PORT=$PORT\"
Environment=\"FLASK_SECRET_KEY=$SECRET_KEY\""

# Add API key if provided
if [[ -n "$API_KEY" ]]; then
    SERVICE_CONTENT="${SERVICE_CONTENT}
Environment=\"GEMINI_API_KEY=$API_KEY\""
fi

# Complete the service file
SERVICE_CONTENT="${SERVICE_CONTENT}

[Install]
WantedBy=multi-user.target"

# Write temporary service file
echo "$SERVICE_CONTENT" > gemini-web.service.tmp

# Display summary
echo
echo -e "${BOLD}Service Configuration Summary:${NC}"
echo "User: $CURRENT_USER"
echo "Working Directory: $CURRENT_DIR"
echo "Python Path: $PYTHON_PATH"
echo "Port: $PORT"
echo "Secret Key: ${SECRET_KEY:0:5}***(truncated)"
if [[ -n "$API_KEY" ]]; then
    echo "API Key: ${API_KEY:0:5}***(truncated)"
fi

# Ask for confirmation
echo
read -p "Is this configuration correct? (y/n): " CONFIRM
if [[ $CONFIRM != "y" && $CONFIRM != "Y" ]]; then
    echo -e "${RED}Setup cancelled.${NC}"
    rm gemini-web.service.tmp
    exit 1
fi

# Copy to systemd directory with sudo
echo
echo "Installing service file (you may be asked for sudo password)..."
sudo mv gemini-web.service.tmp /etc/systemd/system/gemini-web.service

# Reload systemd and enable service
echo "Configuring systemd..."
sudo systemctl daemon-reload
sudo systemctl enable gemini-web
sudo systemctl start gemini-web

# Check service status
echo
echo "Checking service status..."
sudo systemctl status gemini-web

echo
echo -e "${GREEN}${BOLD}Setup complete!${NC}"
echo "You can now manage your application with the following commands:"
echo -e "${BOLD}Start:${NC}   sudo systemctl start gemini-web"
echo -e "${BOLD}Stop:${NC}    sudo systemctl stop gemini-web"
echo -e "${BOLD}Restart:${NC} sudo systemctl restart gemini-web"
echo -e "${BOLD}Status:${NC}  sudo systemctl status gemini-web"
echo -e "${BOLD}Logs:${NC}    sudo journalctl -u gemini-web"
echo
echo -e "Your web interface should be available at: ${BOLD}http://localhost:$PORT${NC}"
echo "If you're on a remote machine, you need to access using the machine's IP address."
echo
echo "For more details, see README-CLOUD-SETUP.md" 