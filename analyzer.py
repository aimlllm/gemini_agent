from google import genai
from google.genai import types
import config
import os
import logging
import io
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
        
        # Prepare the prompt
        prompt = self._prepare_prompt(documents, company_name, quarter, year)
        
        logging.info(f"Sending prompt to Gemini (length: {len(prompt)} chars)")
        
        try:
            # Call Gemini API with version-specific handling
            try:
                # Try newer API version
                model = self.client.get_generative_model("gemini-2.5-pro-preview-05-06")
                response = model.generate_content(prompt)
            except AttributeError:
                # Fall back to older API version
                logging.info("Falling back to older Gemini API format")
                generation_config = {
                    "temperature": 0.2,
                    "max_output_tokens": 4096,
                }
                
                response = self.client.generate_content(
                    model="gemini-2.5-pro-preview-05-06",
                    contents=prompt,
                    generation_config=generation_config
                )
            
            # Extract text from response
            if hasattr(response, 'text'):
                analysis = response.text
            elif hasattr(response, 'candidates') and response.candidates:
                analysis = response.candidates[0].content.parts[0].text
            else:
                logging.error("Unexpected response format from Gemini API")
                return "Error: Unexpected response format from Gemini API."
            
            logging.info(f"Received analysis from Gemini (length: {len(analysis)} chars)")
            return analysis
        except Exception as e:
            logging.error(f"Error calling Gemini API: {e}")
            return f"Error: Failed to analyze documents: {e}" 