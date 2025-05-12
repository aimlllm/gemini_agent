from google import genai
from google.genai import types
import config
import os
import logging
import PyPDF2
import binascii

class EarningsAnalyzer:
    def __init__(self):
        # Initialize Gemini API client
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        
        # Load prompt template
        self.prompt_template = self._load_prompt_template()
        
        # Temporary debug logging to check API key (masked for security)
        api_key = config.GEMINI_API_KEY
        if api_key:
            masked_key = api_key[:4] + '*' * (len(api_key) - 8) + api_key[-4:] if len(api_key) > 8 else "***"
            logging.info(f"API key loaded: {masked_key}")
        else:
            logging.error("No API key found in configuration")
    
    def _load_prompt_template(self):
        """Load the prompt template from the configuration file."""
        try:
            with open(config.PROMPT_CONFIG_PATH, 'r') as file:
                prompt_template = file.read()
                logging.info(f"Loaded prompt template from {config.PROMPT_CONFIG_PATH}")
                return prompt_template
        except Exception as e:
            logging.error(f"Failed to load prompt template: {e}")
            # Fallback to default prompt if file cannot be loaded
            return """
            You are a strategic analyst for Google Cloud Platform, analyzing {company_name}'s {quarter} {year} earnings documents.
            
            Create an email-ready analysis focusing on:
            - Financial Overview
            - Cloud Strategy and Competitive Position
            - Technology and AI Investments
            - Customer and Partner Intelligence
            - Strategic Implications for Google/GCP
            
            Format as clean, professional markdown suitable for immediate email distribution.
            """
    
    def _extract_text_from_pdf(self, pdf_path):
        """Extract text from a PDF file."""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                # Extract text from each page
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text() + "\n\n"
                return text
        except Exception as e:
            logging.error(f"Error extracting text from PDF {pdf_path}: {e}")
            return f"[Error extracting text from PDF: {e}]"
    
    def analyze_earnings_documents(self, documents, company_name, quarter, year):
        """
        Analyze earnings documents (release and/or transcript) in a single Gemini API call.
        
        Args:
            documents (dict): Dictionary of document paths by type
                             {'earnings_release': {'path': path1, 'url': url1},
                              'call_transcript': {'path': path2, 'url': url2}}
            company_name (str): Name of the company
            quarter (str): Quarter (Q1, Q2, Q3, Q4)
            year (str): Year
        
        Returns:
            str: Analysis text
        """
        try:
            # Check if we have any documents
            if not documents:
                logging.error("No documents provided for analysis")
                return "Error: No documents provided for analysis."
            
            # Check available documents
            available_types = list(documents.keys())
            logging.info(f"Available documents: {', '.join(available_types)}")
            
            if 'call_transcript' not in available_types:
                logging.warning("Call transcript is not available. Analysis will be based only on earnings release.")
            elif 'earnings_release' not in available_types:
                logging.warning("Earnings release is not available. Analysis will be based only on call transcript.")
            
            # Initialize Gemini model
            model = "gemini-2.5-pro-preview-05-06"
            
            # Read each document and add it to the input
            parts = []
            
            # Add each document to the parts
            for doc_type, doc_info in documents.items():
                file_path = doc_info['path']
                
                # Check if file exists
                if not os.path.exists(file_path):
                    logging.warning(f"File not found: {file_path}. Skipping.")
                    continue
                
                # Determine file MIME type
                mime_type = self._get_mime_type(file_path)
                
                # Label what type of document this is
                doc_label = "earnings release" if doc_type == "earnings_release" else "earnings call transcript"
                parts.append(types.Part(text=f"\nDOCUMENT TYPE: {doc_label.upper()}\n"))
                
                # Read the file as binary
                try:
                    with open(file_path, 'rb') as f:
                        file_data = f.read()
                    
                    # If file is too large (over 1MB), extract text and use that instead
                    if len(file_data) > 1000000:
                        logging.warning(f"File {file_path} is very large ({len(file_data)} bytes). Extracting text instead of using binary content.")
                        if file_path.lower().endswith('.pdf'):
                            text_content = self._extract_text_from_pdf(file_path)
                        else:
                            # For non-PDF files, try to read as text
                            with open(file_path, 'r', encoding='utf-8', errors='replace') as text_file:
                                text_content = text_file.read()
                        
                        # Truncate if still too large
                        if len(text_content) > 500000:
                            text_content = text_content[:500000] + "\n\n[Content truncated due to length...]"
                        
                        parts.append(types.Part(text=text_content))
                    else:
                        # Use binary content for smaller files
                        parts.append(
                            types.Part(
                                inline_data=types.Blob(
                                    mime_type=mime_type,
                                    data=file_data
                                )
                            )
                        )
                    logging.info(f"Successfully loaded {doc_label}: {os.path.basename(file_path)}")
                except Exception as e:
                    logging.error(f"Error reading {file_path}: {str(e)}")
            
            # Add the consolidated analysis prompt from template
            prompt = self.prompt_template.format(
                company_name=company_name,
                quarter=quarter,
                year=year
            )
            parts.append(types.Part(text=prompt))
            
            # Create content with all documents and prompt
            content = types.Content(parts=parts)
            
            # Generate content with a single API call
            logging.info(f"Sending prompt to Gemini (length: {sum(len(str(p)) for p in parts)} chars)")
            
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=content
                )
                
                if not response or not hasattr(response, 'text') or not response.text:
                    logging.error("Received empty response from Gemini API. Retrying with simplified content...")
                    
                    # Simplify the request - use text extraction for all documents
                    simplified_parts = [types.Part(text=f"\nANALYSIS REQUEST FOR {company_name}'s {quarter} {year} EARNINGS\n\n")]
                    
                    for doc_type, doc_info in documents.items():
                        file_path = doc_info['path']
                        if not os.path.exists(file_path):
                            continue
                            
                        doc_label = "EARNINGS RELEASE" if doc_type == "earnings_release" else "EARNINGS CALL TRANSCRIPT"
                        simplified_parts.append(types.Part(text=f"\n{doc_label}:\n"))
                        
                        try:
                            if file_path.lower().endswith('.pdf'):
                                text_content = self._extract_text_from_pdf(file_path)
                            else:
                                with open(file_path, 'r', encoding='utf-8', errors='replace') as text_file:
                                    text_content = text_file.read()
                            
                            # Truncate content to ensure it's not too large
                            if len(text_content) > 100000:
                                text_content = text_content[:100000] + "\n\n[Content truncated...]"
                                
                            simplified_parts.append(types.Part(text=text_content))
                        except Exception as e:
                            logging.error(f"Error extracting text from {file_path} on retry: {str(e)}")
                    
                    # Add prompt again
                    simplified_parts.append(types.Part(text=prompt))
                    
                    # Create new content
                    simplified_content = types.Content(parts=simplified_parts)
                    
                    # Try again with simplified content
                    logging.info("Retrying with simplified content...")
                    response = self.client.models.generate_content(
                        model=model,
                        contents=simplified_content
                    )
                
                # Extract text from response
                if hasattr(response, 'text') and response.text:
                    analysis = response.text
                    logging.info(f"Received analysis from Gemini (length: {len(analysis)} chars)")
                    return analysis
                else:
                    logging.error("Failed to generate analysis even with simplified content")
                    return "Error: Gemini API failed to generate analysis. Please try again later."
                
            except Exception as e:
                logging.error(f"Error in Gemini API call: {str(e)}")
                return f"Error: Failed to analyze documents: {str(e)}"
            
        except Exception as e:
            logging.error(f"Error creating analysis: {str(e)}")
            return f"Error: {str(e)}"
    
    def _get_mime_type(self, file_path):
        """Determine MIME type based on file extension"""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.pdf':
            return 'application/pdf'
        elif ext in ['.txt', '.md']:
            return 'text/plain'
        elif ext == '.html':
            return 'text/html'
        elif ext in ['.docx', '.doc']:
            return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        else:
            # Default to text
            return 'text/plain' 