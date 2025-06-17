# GCP Deployment Guide for Gemini Agent

## Prerequisites
- Google Cloud Platform account with billing enabled
- VM instance with Python 3.8+ installed
- Internet access on VM instance
- Gemini Agent service already deployed and configured

## Step 1: Access GCP Console and VM Instance

### 1.1 Log into GCP Console
```bash
# Navigate to Google Cloud Console
https://console.cloud.google.com/

# Select your project or create a new one
# Ensure billing is enabled for the project
```

### 1.2 Access VM Instance
```bash
# Option A: Using GCP Console
1. Navigate to Compute Engine > VM instances
2. Click "SSH" button next to your instance name
3. Browser-based SSH terminal will open

# Option B: Using gcloud CLI (if installed locally)
gcloud compute ssh [INSTANCE_NAME] --zone=[ZONE]

# Option C: Using standard SSH (if configured)
ssh -i [KEY_FILE] [USERNAME]@[EXTERNAL_IP]
```

## Step 2: Deploy Code on VM Instance

### 2.1 Download and Extract Code
```bash
# Download the latest code from GitHub
wget https://github.com/aimlllm/gemini_agent/archive/refs/heads/main.zip

# Extract the zip file
unzip main.zip

# Rename directory for convenience
mv gemini_agent-main gemini_agent

# Change to project directory
cd gemini_agent

# Set permissions
chmod +x *.sh
```

## Step 3: Update Deployment

### 3.1 Pull Latest Code
```bash
# Navigate to project directory
cd /gemini_agent

# Download latest version
wget https://github.com/aimlllm/gemini_agent/archive/refs/heads/main.zip -O latest.zip

# Extract new version
unzip -o latest.zip

# Copy new files (preserve config)
cp -r gemini_agent-main/* .
rm -rf gemini_agent-main latest.zip
```

### 3.2 Restart Service After Update
```bash
# Install any new dependencies
pip3 install -r requirements.txt

# Restart the service
sudo systemctl restart gemini-agent

# Verify it's running
sudo systemctl status gemini-agent
```

## Step 4: Check Application Status

```bash
# Verify service is running
sudo systemctl status gemini-agent

# Check if port 8080 is listening
sudo netstat -tlnp | grep 8080
```
