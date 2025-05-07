from google import genai
from google.genai import types
import config
import os
import logging

class EarningsAnalyzer:
    def __init__(self):
        # Initialize Gemini API client
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
    
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
            
            # Add the consolidated analysis prompt after all documents
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
            
            ## Google and GCP Mentions
            - For each Google or GCP mention, include:
              * Document type (earnings release/call transcript)
              * Exact location (page, section, speaker)
              * Direct quote
              * Strategic implications
            
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