#!/bin/bash

# Make script executable with: chmod +x run_web.sh

# Set default port
PORT=${PORT:-8080}

echo "=== Gemini Earnings Analyzer Web Interface ==="
echo "Starting web server on port $PORT..."

# Run Flask application
python app.py

# If you want to use Gunicorn in production, comment the line above
# and uncomment the line below (install gunicorn first)
# gunicorn -w 4 -b 0.0.0.0:$PORT app:app 