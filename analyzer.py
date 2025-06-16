from google import genai
from google.genai import types
import config
import os
import logging

class EarningsAnalyzer:
    def __init__(self):
        # Initialize Gemini API client
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        
        # Temporary debug logging to check API key (masked for security)
        api_key = config.GEMINI_API_KEY
        if api_key:
            masked_key = api_key[:4] + '*' * (len(api_key) - 8) + api_key[-4:] if len(api_key) > 8 else "***"
            logging.info(f"API key loaded: {masked_key}")
        else:
            logging.error("No API key found in configuration")
    
    def analyze_earnings_documents(self, documents, company_name, quarter, year, is_comparative=False, companies=None):
        """
        Analyze earnings documents (release and/or transcript) in a single Gemini API call.
        
        Args:
            documents (dict): Dictionary of document paths by type
                             {'earnings_release': {'path': path1, 'url': url1},
                              'call_transcript': {'path': path2, 'url': url2}}
                              OR for comparative analysis:
                             {'ticker1_earnings_release': path1, 'ticker1_call_transcript': path2}
            company_name (str): Name of the company, or for comparative, a joined string of names
            quarter (str): Quarter (Q1, Q2, Q3, Q4)
            year (str): Year
            is_comparative (bool): Whether this is a comparative analysis of multiple companies
            companies (list): For comparative analysis, list of company data dictionaries
        
        Returns:
            dict: Analysis results formatted for email
        """
        try:
            # Check if we have any documents
            if not documents:
                raise ValueError(f"No documents provided for {company_name}")
            
            # Initialize Gemini model
            model = "gemini-2.5-pro-preview-05-06"
            
            # Read each document and add it to the input
            parts = []
            
            # Add each document to the parts
            if is_comparative:
                # For comparative analysis, documents are in a different format
                for doc_key, file_path in documents.items():
                    # Extract ticker and document type from the key (e.g., "amzn_earnings_release")
                    parts_key = doc_key.split('_', 1)
                    if len(parts_key) != 2:
                        logging.warning(f"Invalid document key: {doc_key}. Skipping.")
                        continue
                    
                    ticker, doc_type = parts_key
                    
                    # Check if file exists
                    if not os.path.exists(file_path):
                        logging.warning(f"File not found: {file_path}. Skipping.")
                        continue
                    
                    # Determine file MIME type
                    mime_type = self._get_mime_type(file_path)
                    
                    # Find the company name for this ticker
                    company_name_for_doc = ticker.upper()
                    if companies:
                        for company_data in companies:
                            if company_data['ticker'].lower() == ticker.lower():
                                company_name_for_doc = f"{company_data['name']} ({ticker.upper()})"
                                break
                    
                    # Label what type of document this is
                    doc_label = "earnings release" if "earnings_release" in doc_type else "earnings call transcript"
                    parts.append(types.Part(text=f"\nDOCUMENT TYPE: {company_name_for_doc} {doc_label.upper()}\n"))
                    
                    # Read the file as binary
                    try:
                        with open(file_path, 'rb') as f:
                            file_data = f.read()
                            
                        parts.append(
                            types.Part(
                                inline_data=types.Blob(
                                    mime_type=mime_type,
                                    data=file_data
                                )
                            )
                        )
                        logging.info(f"Successfully loaded {company_name_for_doc} {doc_label}: {os.path.basename(file_path)}")
                    except Exception as e:
                        logging.error(f"Error reading {file_path}: {str(e)}")
            else:
                # Standard single-company analysis
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
            
            # Load the custom prompt from config if available
            custom_prompt = None
            if os.path.exists(config.PROMPT_CONFIG_PATH):
                try:
                    with open(config.PROMPT_CONFIG_PATH, 'r', encoding='utf-8') as f:
                        custom_prompt = f.read().strip()
                    logging.info("Using custom prompt from config")
                except Exception as e:
                    logging.error(f"Error reading custom prompt: {str(e)}")
            
            # Add the consolidated analysis prompt after all documents
            if is_comparative:
                # For comparative analysis, use a special prompt
                if custom_prompt:
                    prompt = custom_prompt.format(
                        company_name=company_name,
                        quarter=quarter,
                        year=year
                    )
                    # Add comparative instructions
                    prompt += "\n\n### COMPARATIVE ANALYSIS INSTRUCTIONS:\n"
                    prompt += f"This is a comparative analysis of multiple companies: {company_name}.\n"
                    prompt += "For each section, compare and contrast the companies directly.\n"
                    prompt += "Highlight competitive advantages, differing strategies, and relative performance.\n"
                    prompt += "Include a direct comparison matrix section at the end showing key metrics and strategies side by side.\n"
                else:
                    prompt = f"""
                    You are a strategic analyst for Google Cloud Platform, conducting a comparative analysis of {company_name}'s {quarter} {year} earnings documents.
                    
                    Create an email-ready comparative analysis that analyzes and contrasts all companies, focusing on:
                    
                    ## Executive Summary
                    - One paragraph overview comparing the key differences in performance and cloud strategies
                    
                    ## Financial Performance Comparison
                    - Compare and contrast key financial results with cloud market implications
                    - YoY growth rates comparison in relevant areas (revenue, profit, R&D)
                    - Relative market share and positioning
                    
                    ## Cloud Strategy Comparison
                    - Compare and contrast each company's cloud strategy and market position
                    - Identify strategic direction changes or investments
                    - Analyze competitive positioning against each other and Google Cloud
                    
                    ## Technology and AI Investment Comparison
                    - Compare technology investments that might affect cloud adoption
                    - Contrast AI/ML initiatives that could complement or compete with GCP offerings
                    - Compare data center expansions or efficiency improvements
                    - Contrast enterprise sales strategy changes relevant to cloud providers
                    
                    ## Customer and Partner Intelligence
                    - Compare notable customer wins or losses in cloud services
                    - Contrast partner ecosystem developments relevant to cloud
                    - Identify differences in enterprise customer spending patterns
                    
                    ## Strategic Implications for Google/GCP
                    - Opportunities for Google Cloud based on the comparative analysis
                    - Potential threats to Google Cloud's market position from each company
                    - Recommended actions for GCP leadership in response to this analysis
                    
                    ## Comparative Matrix
                    - Create a table comparing key metrics, strategies, and investments across all companies
                    
                    Format as clean, professional markdown suitable for immediate email distribution.
                    Be concise, data-driven, and actionable, focusing on strategic implications.
                    For each insight, specify the exact source (company, document type and location).
                    
                    IMPORTANT: Do NOT include phrases like "Comparative Analysis" or "Here is an analysis of..." in your response.
                    Start directly with the content and ensure the analysis is self-contained and ready to be sent as is.
                    """
            else:
                # Standard single-company analysis
                if custom_prompt:
                    prompt = custom_prompt.format(
                        company_name=company_name,
                        quarter=quarter,
                        year=year
                    )
                else:
            prompt = f"""
            You are a strategic analyst for Google Cloud Platform, analyzing {company_name}'s {quarter} {year} earnings documents.
            
            Create an email-ready analysis that combines insights from all provided documents, focusing on:
            
            ## Financial Overview
            - Key financial results with cloud market implications
            - YoY growth rates in relevant areas (revenue, profit, R&D)
            
            ## Cloud Strategy and Competitive Position
            - Current cloud strategy and market position
            - Strategic direction changes or investments
            - Competitive positioning against Google Cloud

            ## Technology and AI Investments
            - Technology investments that might affect cloud adoption
            - AI/ML initiatives that could complement or compete with GCP offerings
            - Data center expansions or efficiency improvements
            - Enterprise sales strategy changes relevant to cloud providers
            
            ## Customer and Partner Intelligence
            - Notable customer wins or losses in cloud services
            - Partner ecosystem developments relevant to cloud
            - Changes in enterprise customer spending patterns
            
            ## Strategic Implications for Google/GCP
            - Opportunities for Google Cloud based on these earnings documents
            - Potential threats to Google Cloud's market position
            - Recommended actions for GCP leadership

            Format as clean, professional markdown suitable for immediate email distribution.
            Be concise, data-driven, and actionable, focusing on strategic implications.
            For each insight, specify the exact source (document type and location).
            
            IMPORTANT: Do NOT include phrases like "Executive Summary" or "Here is an analysis of..." in your response.
            Start directly with the content and ensure the analysis is self-contained and ready to be sent as is.
            """
            
            parts.append(types.Part(text=prompt))
            
            # Create content with all documents and prompt
            content = types.Content(parts=parts)
            
            # Generate content with a single API call
            logging.info(f"Sending analysis request to Gemini model: {model}")
            response = self.client.models.generate_content(
                model=model,
                contents=content
            )
            
            logging.info(f"Successfully generated analysis for {company_name}")
            
            # Construct the URLs dictionary for all document types
            if is_comparative:
                document_urls = {doc_key: "multiple documents" for doc_key in documents.keys()}
            else:
            document_urls = {
                doc_type: doc_info['url'] 
                for doc_type, doc_info in documents.items()
            }
            
            return {
                'company': company_name,
                'period': f"{quarter} {year}",
                'document_types': list(documents.keys()),
                'document_urls': document_urls,
                'analysis': response.text
            }
            
        except Exception as e:
            logging.error(f"Error creating analysis: {str(e)}")
            return {
                'company': company_name,
                'period': f"{quarter} {year}",
                'document_types': list(documents.keys()) if documents else [],
                'error': str(e)
            }
    
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