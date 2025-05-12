from google import generativeai as genai
import config
import os
import logging
import io
import PyPDF2
import binascii

class EarningsAnalyzer:
    def __init__(self):
        # Initialize Gemini API client
        genai.configure(api_key=config.GEMINI_API_KEY)
        
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
    
    def _prepare_prompt(self, documents, company_name, quarter, year):
        """Prepare the prompt with document content and company details."""
        # Format the prompt template with company details
        prompt = self.prompt_template.format(
            company_name=company_name,
            quarter=quarter,
            year=year
        )
        
        # Add document content to the prompt
        full_prompt = prompt + "\n\n## Document Content:\n\n"
        
        for doc_type, content in documents.items():
            full_prompt += f"### {doc_type.replace('_', ' ').title()}\n"
            # Handle content that might be a dictionary with 'path' and 'url' keys
            if isinstance(content, dict) and 'path' in content:
                file_path = content['path']
                if file_path.lower().endswith('.pdf'):
                    # Extract text from PDF
                    doc_content = self._extract_text_from_pdf(file_path)
                    # Truncate if too long
                    if len(doc_content) > 100000:
                        doc_content = doc_content[:100000] + "... [content truncated]"
                    full_prompt += doc_content + "\n\n"
                else:
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
                            doc_content = file.read()
                            full_prompt += doc_content + "\n\n"
                    except Exception as e:
                        logging.error(f"Error reading file {file_path}: {e}")
                        full_prompt += f"[Error reading file: {e}]\n\n"
            else:
                # Content is already a string
                full_prompt += str(content) + "\n\n"
        
        return full_prompt
    
    def analyze_earnings_documents(self, documents, company_name, quarter, year):
        """
        Analyze earnings documents for a company.
        
        Args:
            documents (dict): Dictionary with document types as keys and content as values
            company_name (str): Company name
            quarter (str): Quarter (e.g., 'Q1')
            year (str): Year (e.g., '2023')
            
        Returns:
            str: Gemini analysis of the earnings documents
        """
        logging.info(f"Analyzing {company_name} {quarter} {year} earnings documents")
        
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
        
        # Prepare the prompt
        prompt = self._prepare_prompt(documents, company_name, quarter, year)
        
        # Check if prompt is too large
        if len(prompt) > 500000:
            logging.warning(f"Prompt is very large ({len(prompt)} chars). Truncating to 500,000 chars to prevent issues.")
            prompt = prompt[:500000] + "\n\n[Content truncated due to length]"
            
        logging.info(f"Sending prompt to Gemini (length: {len(prompt)} chars)")
        
        try:
            # Use a simple and reliable approach to call Gemini API with version 0.7.2
            model = genai.GenerativeModel(
                model_name="gemini-2.5-pro-preview-05-06",
                generation_config={
                    "temperature": 0.2,
                    "top_p": 0.95,
                    "top_k": 64,
                    "max_output_tokens": 4096,
                }
            )
            
            # Make the API call
            response = model.generate_content(prompt)
            
            # Extract text from response
            if hasattr(response, 'text') and response.text:
                analysis = response.text
                logging.info(f"Received analysis from Gemini (length: {len(analysis)} chars)")
                return analysis
            else:
                logging.error("Received empty response from Gemini API. Retrying with shorter prompt...")
                
                # Try again with a shorter prompt
                shorter_prompt = self._prepare_shortened_prompt(documents, company_name, quarter, year)
                logging.info(f"Retrying with shorter prompt (length: {len(shorter_prompt)} chars)")
                
                response = model.generate_content(shorter_prompt)
                
                if hasattr(response, 'text') and response.text:
                    analysis = response.text
                    logging.info(f"Received analysis from Gemini on retry (length: {len(analysis)} chars)")
                    return analysis
                else:
                    logging.error("Failed to generate analysis even with shortened prompt")
                    return "Error: Gemini API failed to generate analysis. Please try again later."
            
        except Exception as e:
            logging.error(f"Error calling Gemini API: {e}")
            return f"Error: Failed to analyze documents: {e}"
    
    def _prepare_shortened_prompt(self, documents, company_name, quarter, year):
        """Prepare a shortened prompt with less document content."""
        # Format the prompt template with company details
        prompt = self.prompt_template.format(
            company_name=company_name,
            quarter=quarter,
            year=year
        )
        
        # Add a note about truncation
        full_prompt = prompt + "\n\n## Document Content (Truncated):\n\n"
        
        # Add only portions of each document
        for doc_type, content in documents.items():
            full_prompt += f"### {doc_type.replace('_', ' ').title()}\n"
            
            # Handle dictionaries with path
            if isinstance(content, dict) and 'path' in content:
                file_path = content['path']
                
                if file_path.lower().endswith('.pdf'):
                    # Extract only first few pages from PDF
                    try:
                        text = self._extract_text_from_pdf(file_path)
                        # Take only first 50,000 characters
                        text = text[:50000] + "... [content truncated]"
                        full_prompt += text + "\n\n"
                    except Exception as e:
                        full_prompt += f"[Error extracting text: {e}]\n\n"
                else:
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
                            text = file.read()
                            # Take only first 50,000 characters
                            text = text[:50000] + "... [content truncated]"
                            full_prompt += text + "\n\n"
                    except Exception as e:
                        full_prompt += f"[Error reading file: {e}]\n\n"
            else:
                # Content is already a string, truncate it
                text = str(content)
                text = text[:50000] + "... [content truncated]"
                full_prompt += text + "\n\n"
        
        # Add note about truncation
        full_prompt += "\n\nNote: Document content has been truncated to ensure successful processing. Please focus on the most important insights from the available content."
        
        return full_prompt 