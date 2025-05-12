import os
import base64
import json
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import markdown
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pickle
import config

class EmailService:
    """Service for sending emails using Gmail API."""
    
    def __init__(self, config_path=None):
        """
        Initialize the EmailService with configuration from JSON file.
        
        Args:
            config_path (str, optional): Path to the email configuration JSON file
                                         Defaults to value from config.py
        """
        # Load email configuration
        if config_path is None:
            config_path = config.EMAIL_CONFIG_PATH
            
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
        except Exception as e:
            logging.error(f"Error loading email configuration: {e}")
            self.config = {
                "enabled": False,
                "recipients": [],
                "credentials_path": config.GMAIL_CREDENTIALS_PATH,
                "token_path": "token.pickle"
            }
        
        # Process credential paths (handle environment variable references)
        self.credentials_path = self._resolve_env_reference(
            self.config.get("credentials_path", config.GMAIL_CREDENTIALS_PATH)
        )
        self.token_path = self._resolve_env_reference(
            self.config.get("token_path", "token.pickle")
        )
        
        # Get client ID and secret from environment variables
        self.client_id = os.getenv('GMAIL_CLIENT_ID')
        self.client_secret = os.getenv('GMAIL_CLIENT_SECRET')
        
        # Use the correct scope for Gmail sending with profile access
        # https://mail.google.com/ is the broadest scope that includes all Gmail permissions
        self.scopes = ['https://mail.google.com/']
        
        self.creds = None
        self.service = None
    
    def _resolve_env_reference(self, value):
        """
        Resolve a string value that might reference an environment variable.
        Also expands the home directory for paths that include ~.
        
        Args:
            value (str): String value that might be in format ".env:VAR_NAME"
            
        Returns:
            str: The resolved value
        """
        if isinstance(value, str) and value.startswith(".env:"):
            env_var = value.split(":", 1)[1]
            value = os.getenv(env_var, value)
            
        # Expand home directory if path contains tilde
        if isinstance(value, str) and '~' in value:
            value = os.path.expanduser(value)
            
        return value
    
    def authenticate(self, force_refresh=False):
        """
        Authenticate with Gmail API using OAuth2.
        
        Args:
            force_refresh (bool): Force a new authentication flow even if credentials exist
                                  Useful when scopes have changed
                                  
        Returns:
            bool: True if authentication was successful, False otherwise
        """
        # If force_refresh, delete the token file
        if force_refresh and os.path.exists(self.token_path):
            try:
                os.remove(self.token_path)
                logging.info(f"Deleted token file due to force_refresh: {self.token_path}")
            except Exception as e:
                logging.error(f"Error deleting token file: {e}")
        
        # Check if we have valid credentials saved
        if os.path.exists(self.token_path) and not force_refresh:
            try:
                with open(self.token_path, 'rb') as token:
                    self.creds = pickle.load(token)
            except Exception as e:
                logging.error(f"Error loading credentials from token file: {e}")
                self.creds = None
        
        # If there are no valid credentials, let the user log in
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except Exception as e:
                    logging.error(f"Error refreshing token: {e}")
                    # Token refresh failed, need to reauthenticate
                    self.creds = None
            
            # If still no valid credentials, run the OAuth flow
            if not self.creds:
                # Check if credentials.json exists
                logging.info(f"Looking for credentials file at: {self.credentials_path}")
                if not os.path.exists(self.credentials_path):
                    logging.error(f"Credentials file not found: {self.credentials_path}")
                    logging.error("Please download credentials.json from Google Cloud Console")
                    logging.error("and place it in the specified location.")
                    return False
                
                logging.info(f"Starting OAuth flow with credentials from: {self.credentials_path}")
                logging.info("A browser window will open for authentication. Please:")
                logging.info("1. Sign in with your Google account")
                logging.info("2. Review the requested permissions (scope: https://mail.google.com/)")
                logging.info("3. Click 'Allow' to grant access")
                logging.info("4. Return to this terminal after authentication completes")
                
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, self.scopes)
                    
                    # Use fixed port 8080 instead of random port (port=0)
                    # This way, the port can be forwarded via SSH
                    logging.info("Please authenticate in your browser at: http://localhost:8080")
                    logging.info("If using SSH port forwarding, the browser should open on your local machine")
                    self.creds = flow.run_local_server(port=8080, open_browser=False)
                    
                    # Save the credentials for the next run
                    with open(self.token_path, 'wb') as token:
                        pickle.dump(self.creds, token)
                    
                    logging.info("Successfully obtained new OAuth credentials")
                except Exception as e:
                    logging.error(f"Error during OAuth flow: {e}")
                    return False
        
        try:
            # Build the Gmail service
            self.service = build('gmail', 'v1', credentials=self.creds)
            
            # Test the service by listing labels
            self.service.users().labels().list(userId='me').execute()
            
            logging.info("Successfully authenticated with Gmail API")
            return True
        except Exception as e:
            logging.error(f"Error initializing Gmail API service: {e}")
            
            # If this wasn't a force refresh attempt, try force refreshing
            if not force_refresh:
                logging.info("Authentication failed, trying with force_refresh=True")
                return self.authenticate(force_refresh=True)
            
            return False
    
    def send_gcp_impact_email(self, markdown_file_path, subject=None):
        """
        Send GCP impact analysis email using Gmail API and config file settings.
        
        Args:
            markdown_file_path (str): Path to the markdown file containing the analysis
            subject (str, optional): Email subject (defaults to derived from markdown content)
            
        Returns:
            dict: Result of the send operation
        """
        # Check if email sending is enabled in config
        if not self.config.get("enabled", False):
            logging.info("Email sending is disabled in configuration")
            return {
                'success': False,
                'error': 'Email sending is disabled in configuration'
            }
        
        # Get recipients from config
        recipients = self.config.get("recipients", [])
        cc_recipients = self.config.get("cc", [])
        
        if not recipients:
            logging.error("No recipients configured in email_config.json")
            return {
                'success': False,
                'error': 'No recipients configured'
            }
        
        try:
            if not self.service:
                if not self.authenticate():
                    return {
                        'success': False,
                        'error': 'Authentication failed'
                    }
            
            # Read the markdown file
            with open(markdown_file_path, 'r') as f:
                markdown_content = f.read()
            
            # Extract title for subject if not provided
            if not subject:
                # Try to extract the title from markdown (assumes first line is a heading)
                lines = markdown_content.split('\n')
                for line in lines:
                    if line.startswith('# '):
                        subject = line.replace('# ', '')
                        break
                    
                # Fallback subject if extraction fails
                if not subject:
                    subject = "GCP Impact Analysis"
            
            # Add subject prefix if configured
            subject_prefix = self.config.get("email_subject_prefix", "")
            if subject_prefix and not subject.startswith(subject_prefix):
                subject = f"{subject_prefix}{subject}"
            
            # Create message container
            message = MIMEMultipart('alternative')
            message['Subject'] = subject
            
            # Get sender email (authenticated user's email)
            try:
                profile = self.service.users().getProfile(userId='me').execute()
                sender = profile['emailAddress']
            except Exception as e:
                # Fallback to configured sender email
                logging.warning(f"Could not get user profile: {e}")
                sender = self.config.get("sender_email", os.getenv("DEFAULT_SENDER_EMAIL", "example@gmail.com"))
                logging.info(f"Using fallback sender email: {sender}")
                
            message['From'] = sender
            message['To'] = ', '.join(recipients)
            
            if cc_recipients:
                message['Cc'] = ', '.join(cc_recipients)
            
            # Convert markdown to HTML if enabled
            html_enabled = self.config.get("html_enabled", True)
            
            # Create the plain-text version
            text_part = MIMEText(markdown_content, 'plain')
            message.attach(text_part)
            
            # Create HTML version if enabled
            if html_enabled:
                html_content = markdown.markdown(
                    markdown_content,
                    extensions=['tables', 'fenced_code', 'codehilite']
                )
                html_part = MIMEText(html_content, 'html')
                message.attach(html_part)
            
            # Encode message in base64
            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # Create the message for Gmail API
            created_message = {
                'raw': encoded_message
            }
            
            # Send the message
            sent_message = self.service.users().messages().send(
                userId='me', body=created_message).execute()
            
            # Log success with all recipients (to + cc)
            all_recipients = recipients + cc_recipients
            logging.info(f"GCP impact analysis email sent to {', '.join(all_recipients)}")
            
            return {
                'success': True,
                'message_id': sent_message['id'],
                'recipients': recipients,
                'cc': cc_recipients,
                'subject': subject
            }
            
        except HttpError as error:
            logging.error(f"Error sending email: {error}")
            return {
                'success': False,
                'error': str(error)
            }
        except Exception as e:
            logging.error(f"Unexpected error sending email: {e}")
            return {
                'success': False,
                'error': str(e)
            }

def send_analysis_email(markdown_file_path, config_path=None, force_refresh=False):
    """
    Convenience function to send GCP impact analysis email using config file.
    
    Args:
        markdown_file_path (str): Path to the markdown file containing the analysis
        config_path (str, optional): Path to the email configuration JSON file
                                    Defaults to value from config.py
        force_refresh (bool): Whether to force reauthentication
        
    Returns:
        dict: Result of the send operation
    """
    email_service = EmailService(config_path=config_path)
    
    if email_service.authenticate(force_refresh=force_refresh):
        return email_service.send_gcp_impact_email(markdown_file_path)
    else:
        logging.error("Failed to authenticate with Gmail API")
        return {
            'success': False,
            'error': 'Authentication failed'
        } 