# Running the Partner S&O Earnings Reader on Google Cloud

This guide explains how to set up and manage the Partner S&O Earnings Reader web interface on a Google Cloud VM instance. These instructions are designed for users who are not software engineers.

## Initial Setup (One-time Setup)

### 1. Set Up the Service

1. Connect to your Google Cloud VM using SSH

2. Create a service file by running this command:
   ```
   sudo nano /etc/systemd/system/gemini-web.service
   ```

3. Copy and paste the following text (replace parts in UPPERCASE with your actual values):
   ```
   [Unit]
   Description=Partner S&O Earnings Reader Web Interface
   After=network.target

   [Service]
   User=YOUR_USERNAME
   WorkingDirectory=/path/to/gemini_agent
   ExecStart=/path/to/YOUR_VENV/bin/python /path/to/gemini_agent/app.py
   Restart=always
   RestartSec=10
   Environment="PORT=8080"
   Environment="FLASK_SECRET_KEY=your-secure-secret-key"
   Environment="GEMINI_API_KEY=your-gemini-api-key"

   [Install]
   WantedBy=multi-user.target
   ```

4. Save the file by pressing `Ctrl+X`, then `Y`, then `Enter`

5. Load the service by running:
   ```
   sudo systemctl daemon-reload
   sudo systemctl enable gemini-web
   ```

## Everyday Usage

### Starting the Application

To start the application, run:
```
sudo systemctl start gemini-web
```

You should see no output if successful. To verify it's running:
```
sudo systemctl status gemini-web
```
Look for "active (running)" in green text.

### Stopping the Application

To stop the application, run:
```
sudo systemctl stop gemini-web
```

### Restarting the Application

If you need to restart (after making changes to the code):
```
sudo systemctl restart gemini-web
```

### Checking if the App is Running

To check the status of the application:
```
sudo systemctl status gemini-web
```

You should see something like:
```
● gemini-web.service - Partner S&O Earnings Reader Web Interface
     Loaded: loaded (/etc/systemd/system/gemini-web.service; enabled; vendor preset: enabled)
     Active: active (running) since Mon 2023-07-10 15:30:45 UTC; 2h 5min ago
```

### Viewing Application Errors

If the application isn't working correctly, check the error logs:
```
sudo journalctl -u gemini-web.service -n 50
```

## Accessing the Web Interface

Once the application is running, you can access it by:

1. **Within the same network**: Visit `http://VM-INTERNAL-IP:8080`
2. **From anywhere**: Visit `http://VM-EXTERNAL-IP:8080` (if your firewall allows it)

## Common Tasks

### After Making Code Changes

If you update the application code, restart the service to apply changes:
```
sudo systemctl restart gemini-web
```

### If the Application Crashes

Check the status and logs:
```
sudo systemctl status gemini-web
sudo journalctl -u gemini-web.service -n 100
```

Then restart the service:
```
sudo systemctl restart gemini-web
```

### Automatically Start on VM Boot

The service is already configured to start automatically when the VM boots. If you need to disable this:
```
sudo systemctl disable gemini-web
```

## Quick Reference Card

Print this section for easy reference:

```
┌─────────────────────────────────────────────────┐
│ Partner S&O Earnings Reader - Quick Commands    │
├─────────────────────────────────────────────────┤
│ Start application:   sudo systemctl start gemini-web   │
│ Stop application:    sudo systemctl stop gemini-web    │
│ Restart application: sudo systemctl restart gemini-web │
│ Check status:        sudo systemctl status gemini-web  │
│ View logs:           sudo journalctl -u gemini-web     │
├─────────────────────────────────────────────────┤
│ Web address: http://YOUR-VM-IP:8080             │
└─────────────────────────────────────────────────┘
```

## Troubleshooting

### Application Won't Start

1. Check if your virtual environment path is correct in the service file
2. Ensure all required Python packages are installed
3. Check permissions on the application directory
4. Look at the logs for specific errors:
   ```
   sudo journalctl -u gemini-web.service -n 100
   ```

### Can't Access Web Interface

1. Make sure the application is running (`sudo systemctl status gemini-web`)
2. Check if port 8080 is allowed in your Google Cloud firewall rules
3. Try accessing from the VM itself using `curl http://localhost:8080`

### Need to Change Configuration

If you need to change the service configuration:
1. Edit the service file: `sudo nano /etc/systemd/system/gemini-web.service`
2. Reload systemd: `sudo systemctl daemon-reload`
3. Restart the service: `sudo systemctl restart gemini-web` 