import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from langchain.docstore.document import Document
from src.types import GraphState
from src.utils.fireworks_client import FireworksClient
from src.utils.deepseek_client import DeepseekClient
from src.prompts.target_report_templates import (
    COMPANY_OVERVIEW_TEMPLATE,
    OPEN_POSITIONS_TEMPLATE,
    NEWS_TEMPLATE,
    MACRO_TRENDS_TEMPLATE,
    TARGET_REPORT_TEMPLATE,
    TARGET_VERIFICATION_PROMPT,
    TARGET_FOCUS_AREAS
)

def generate_section_with_deepseek(self, prompt: str, section_name: str) -> str:
    """Generate a report section using the Deepseek API directly or via Fireworks.ai."""
    # Import required modules at function level to prevent UnboundLocalError
    import os
    import re
    import tiktoken
    from openai import OpenAI
    
    try:
        # Create output directory if it doesn't exist
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'output')
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate timestamp and filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'prompt_target_{section_name.lower().replace(" ", "_")}_{timestamp}.txt'
        filepath = os.path.join(output_dir, filename)
        
        # Prepare system message
        system_msg = "You are a business intelligence AI that generates high-quality, factual reports about companies based on provided information."
        system_msg_with_section = f"{system_msg} You're now generating the {section_name} section."
        
        # Write prompt to file
        with open(filepath, 'w') as f:
            f.write("=== DEVELOPER MESSAGE ===\n")
            f.write(system_msg_with_section)
            f.write("\n\n=== USER MESSAGE ===\n")
            f.write(prompt)
            f.write("\n=== END PROMPT ===\n")
        
        print(f"INFO [[generate_section_with_deepseek]]: Saved {section_name} prompt to {filepath}")
        
        # Initialize tokenizer for token counting
        encoder = tiktoken.get_encoding("cl100k_base")
        
        # Calculate tokens in system message and prompt template
        system_tokens = len(encoder.encode(system_msg_with_section))
        
        # Calculate available tokens for content
        MAX_TOKENS = 65536  # Deepseek's limit
        RESPONSE_BUFFER = 4000  # Reserve tokens for response
        available_tokens = MAX_TOKENS - system_tokens - RESPONSE_BUFFER
        
        # Encode and potentially truncate prompt
        prompt_tokens = encoder.encode(prompt)
        if len(prompt_tokens) > available_tokens:
            print(f"WARNING [[generate_section_with_deepseek]]: Truncating prompt from {len(prompt_tokens)} to {available_tokens} tokens")
            prompt = encoder.decode(prompt_tokens[:available_tokens])
        
        # Prepare messages
        messages = [
            {
                "role": "developer",
                "content": system_msg_with_section
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        # First try with Deepseek API
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if api_key:
            # Try up to 2 times with Deepseek API
            attempts = 0
            max_attempts = 2
            last_error = None
            
            while attempts < max_attempts:
                try:
                    # Initialize Deepseek client
                    deepseek_client = DeepseekClient(api_key=api_key)
                    
                    # Get completion from Deepseek
                    section_content = deepseek_client.chat_completion(messages)
                    print(f"INFO [[generate_section_with_deepseek]]: Generated {section_name} section using DeepSeek API (attempt {attempts+1})")
                    
                    # Strip markdown code block markers if present
                    section_content = self._strip_markdown_code_blocks(section_content)
                    
                    return section_content
                except Exception as e:
                    last_error = e
                    attempts += 1
                    print(f"WARNING [[generate_section_with_deepseek]]: Error with DeepSeek API (attempt {attempts}): {str(e)}")
                    if attempts < max_attempts:
                        print(f"INFO [[generate_section_with_deepseek]]: Retrying with DeepSeek API...")
            
            print(f"WARNING [[generate_section_with_deepseek]]: All DeepSeek API attempts failed. Last error: {str(last_error)}")
        else:
            print(f"WARNING [[generate_section_with_deepseek]]: DeepSeek API key not configured")
        
        # Fall back to Fireworks if DeepSeek attempts failed or key not available
        fireworks_api_key = os.getenv("FIREWORKS_API_KEY")
        if fireworks_api_key:
            try:
                # Initialize Fireworks client
                fireworks_client = FireworksClient(api_key=fireworks_api_key)
                
                # Get completion from Fireworks
                section_content = fireworks_client.chat_completion(messages)
                print(f"INFO [[generate_section_with_deepseek]]: Generated {section_name} section using Fireworks.ai as fallback")
                
                # Strip markdown code block markers if present
                section_content = self._strip_markdown_code_blocks(section_content)
                
                return section_content
            except Exception as e:
                print(f"WARNING [[generate_section_with_deepseek]]: Error with Fireworks.ai fallback: {str(e)}")
                print(f"INFO [[generate_section_with_deepseek]]: Falling back to default model")
        else:
            print(f"WARNING [[generate_section_with_deepseek]]: Neither DeepSeek nor Fireworks API keys configured")
            print(f"INFO [[generate_section_with_deepseek]]: Falling back to default model")
        
        # Fall back to default model if both Deepseek and Fireworks fail or keys not available
        try:
            # Use OpenAI client directly
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            # Format messages for OpenAI API - keep original roles (including "developer")
            api_messages = []
            for message in messages:
                api_messages.append({"role": message["role"], "content": message["content"]})
            
            # Call API without temperature parameter
            response = client.chat.completions.create(
                model="o3-mini",
                messages=api_messages if len(api_messages) > 0 else [{"role": "user", "content": messages[-1]["content"]}],
            )
            
            section_content = response.choices[0].message.content
            print(f"INFO [[generate_section_with_deepseek]]: Generated {section_name} section using default OpenAI model (o3-mini)")
            
            # Strip markdown code block markers if present
            section_content = self._strip_markdown_code_blocks(section_content)
            
            return section_content
        except Exception as e:
            print(f"ERROR [[generate_section_with_deepseek]]: Error with default model: {str(e)}")
            return f"## {section_name}\nError generating section content: API errors with DeepSeek, Fireworks, and default model."
    except Exception as e:
        print(f"ERROR [[generate_section_with_deepseek]]: Error generating {section_name} section: {str(e)}")
        return f"## {section_name}\nError generating section content: {str(e)}"

# Helper function to strip markdown code blocks
def _strip_markdown_code_blocks(self, content: str) -> str:
    """Strip markdown code block markers from the given content."""
    # Import re module at method level to prevent UnboundLocalError
    import re
    
    if not content:
        return content
    
    # Remove triple backtick markdown blocks
    content = re.sub(r'```(?:markdown)?\s*\n', '', content)
    content = re.sub(r'\n```', '', content)
    
    return content

def generate_target_company_report(self, state: GraphState) -> GraphState:
    """Generate a target company report with separate sections."""
    try:
        print("DEBUG [[generate_target_company_report]]: Creating documents for target company report")
        
        # Check if we already have target_report_data in state
        if "target_report_data" in state:
            print("DEBUG [[generate_target_company_report]]: target_report_data already exists in state, skipping document creation")
            return state
            
        # Initial document gathering
        webpage_docs = self.get_webpage_docs(state, "target")
        news_docs = self.get_news_docs(state, "target")
        job_listings_docs = []
        macro_trends_docs = []
        company_url = state["inputs"].get("target_url", "")
        company_name = self.get_company_name_from_url(company_url)
        user_company_name = self.get_company_name_from_url(state["inputs"].get("user_url", ""))

        # Get job listings documents
        if "job_listings" in state["branches"]["target"]:
            for job in state["branches"]["target"]["job_listings"]:
                # Create metadata dictionary
                metadata = {
                    "title": job.get("title"),
                    "location": job.get("location"),
                    "department": job.get("department"),
                    "source_url": job.get("url", ""),
                    "source_type": "job_listing"
                }
                # Filter out None values
                metadata = {k: v for k, v in metadata.items() if v is not None}
                
                # Create Document
                doc = Document(
                    page_content=job.get("description", "") or job.get("text", ""),
                    metadata=metadata
                )
                job_listings_docs.append(doc)
            print(f"DEBUG [[generate_target_company_report]]: Added {len(job_listings_docs)} job listing documents")
        else:
            print("WARNING: No job listings found for target company")

        # Get macro trends documents
        if "macro_trends_data" in state["branches"]["target"]:
            print(f"DEBUG [[generate_target_company_report]]: Found macro_trends_data in state with {len(state['branches']['target']['macro_trends_data'].get('main', []))} items")
            
            # Log the first few items for debugging
            for i, trend in enumerate(state["branches"]["target"]["macro_trends_data"].get("main", [])[:3]):
                print(f"DEBUG [[generate_target_company_report]]: Macro trend {i+1}: {trend.get('title', 'No title')} | URL: {trend.get('url', 'No URL')}")
            
            for trend in state["branches"]["target"]["macro_trends_data"].get("main", []):
                # Create metadata dictionary
                metadata = {
                    "title": trend.get("title"),
                    "published_date": trend.get("published"),
                    "source_url": trend.get("url", ""),
                    "source_type": "macro_trend"
                }
                # Filter out None values
                metadata = {k: v for k, v in metadata.items() if v is not None}
                
                # Create Document
                doc = Document(
                    page_content=trend.get("text", "") or trend.get("summary", ""),
                    metadata=metadata
                )
                macro_trends_docs.append(doc)
            print(f"DEBUG [[generate_target_company_report]]: Added {len(macro_trends_docs)} macro trends documents")
        else:
            print("WARNING [[generate_target_company_report]]: No macro_trends_data found in state['branches']['target']")
            # Check if there are other keys that might contain macro trends data
            print(f"DEBUG [[generate_target_company_report]]: Available keys in state['branches']['target']: {list(state['branches']['target'].keys())}")
            
            # Check if macro_trends exists
            if "macro_trends" in state["branches"]["target"]:
                print(f"DEBUG [[generate_target_company_report]]: Found macro_trends key with type: {type(state['branches']['target']['macro_trends'])}")
                if isinstance(state["branches"]["target"]["macro_trends"], dict):
                    print(f"DEBUG [[generate_target_company_report]]: macro_trends keys: {list(state['branches']['target']['macro_trends'].keys())}")
                    
                    # Try to use this data instead
                    if "main" in state["branches"]["target"]["macro_trends"]:
                        print(f"DEBUG [[generate_target_company_report]]: Using macro_trends.main instead of macro_trends_data")
                        for trend in state["branches"]["target"]["macro_trends"].get("main", []):
                            metadata = {
                                "title": trend.get("title"),
                                "published_date": trend.get("published"),
                                "source_url": trend.get("url", ""),
                                "source_type": "macro_trend"
                            }
                            # Filter out None values
                            metadata = {k: v for k, v in metadata.items() if v is not None}
                            
                            # Create Document
                            doc = Document(
                                page_content=trend.get("text", "") or trend.get("summary", ""),
                                metadata=metadata
                            )
                            macro_trends_docs.append(doc)
                        print(f"DEBUG [[generate_target_company_report]]: Added {len(macro_trends_docs)} macro trends documents from macro_trends.main")
            
            if len(macro_trends_docs) == 0:
                print("WARNING: No macro trends found for target company")

        # Store documents in state to avoid redundant creation
        state["target_webpage_docs"] = webpage_docs
        state["target_news_docs"] = news_docs
        state["target_job_listings_docs"] = job_listings_docs
        state["target_macro_trends_docs"] = macro_trends_docs

        # Get user company report from state
        user_report = state["branches"]["user"].get("report", "No user company report available")

        # Generate metadata and citations directly without using execute_rag_process
        # This simplifies the flow and avoids unnecessary LLM calls
        source_metadata = {}
        index = 1
        
        # Add webpage docs to metadata
        for doc in webpage_docs:
            if doc.metadata.get("source_url") and doc.metadata.get("source_url") not in source_metadata:
                source_metadata[doc.metadata["source_url"]] = {
                    "index": index,
                    "title": doc.metadata.get("title", "Webpage"),
                    "type": "webpage"
                }
                index += 1
        
        # Add news docs to metadata
        for doc in news_docs:
            if doc.metadata.get("source_url") and doc.metadata.get("source_url") not in source_metadata:
                source_metadata[doc.metadata["source_url"]] = {
                    "index": index,
                    "title": doc.metadata.get("title", "News Article"),
                    "type": "news",
                    "published_date": doc.metadata.get("published_date", "Unknown date")
                }
                index += 1
        
        # Add job docs to metadata
        for doc in job_listings_docs:
            if doc.metadata.get("source_url") and doc.metadata.get("source_url") not in source_metadata:
                source_metadata[doc.metadata["source_url"]] = {
                    "index": index,
                    "title": doc.metadata.get("title", "Job Listing"),
                    "type": "job"
                }
                index += 1
        
        # Add macro docs to metadata
        for doc in macro_trends_docs:
            if doc.metadata.get("source_url") and doc.metadata.get("source_url") not in source_metadata:
                source_metadata[doc.metadata["source_url"]] = {
                    "index": index,
                    "title": doc.metadata.get("title", "Macro Trend"),
                    "type": "macro"
                }
                index += 1
        
        # Generate citations list
        sorted_citations = []
        for url, metadata in sorted(source_metadata.items(), key=lambda x: x[1]['index']):
            citation = f"[{metadata['index']}]. [{metadata['title']}]({url}) - {url}"
            if metadata['type'] == 'news':
                citation += f" - News article from {metadata.get('published_date', 'Unknown date')}"
            sorted_citations.append(citation)
        
        # Join citations with <br> tags to ensure proper line breaks
        citations = "<br>\n".join(sorted_citations) + "<br>"
        
        # Prepare context for each document type with consistent citations
        macro_context = "\n\n".join([
            f"{d.page_content} [Citation: {source_metadata.get(d.metadata.get('source_url'), {}).get('index', '?')}]" 
            for d in macro_trends_docs 
            if d.metadata.get('source_url') and d.metadata.get('source_url') in source_metadata
        ])
        
        news_context = "\n\n".join([
            f"{d.page_content} [Citation: {source_metadata.get(d.metadata.get('source_url'), {}).get('index', '?')}]" 
            for d in news_docs 
            if d.metadata.get('source_url') and d.metadata.get('source_url') in source_metadata
        ])
        
        webpage_context = "\n\n".join([
            f"{d.page_content} [Citation: {source_metadata.get(d.metadata.get('source_url'), {}).get('index', '?')}]" 
            for d in webpage_docs 
            if d.metadata.get('source_url') and d.metadata.get('source_url') in source_metadata
        ])
        
        job_context = "\n\n".join([
            f"{d.page_content} [Citation: {source_metadata.get(d.metadata.get('source_url'), {}).get('index', '?')}]" 
            for d in job_listings_docs 
            if d.metadata.get('source_url') and d.metadata.get('source_url') in source_metadata
        ])
        
        # Ensure job_context is always present, even if empty
        if not job_context:
            job_context = "No job listings found."
            print("DEBUG [[generate_target_company_report]]: No job context found, using default empty value")
            
        # Store template variables and metadata in state for use by the graph nodes
        state["target_report_data"] = {
            "company_name": company_name,
            "user_company_name": user_company_name,
            "macro_context": macro_context,
            "news_context": news_context,
            "webpage_context": webpage_context,
            "job_context": job_context,
            "citations": citations,
            "user_report": user_report,
            "hiring_info_context": state["branches"]["target"].get("hiring_info", []),
            "source_metadata": source_metadata
        }
        
        print("DEBUG [[generate_target_company_report]]: Prepared target report data for graph nodes")
        print(f"DEBUG [[generate_target_company_report]]: target_report_data keys: {list(state['target_report_data'].keys())}")
        
        # Initialize sections dictionary to store generated sections
        state["sections"] = {}
        
        return state
    except Exception as e:
        print(f"ERROR [[generate_target_company_report]]: Error generating target company report: {str(e)}")
        raise