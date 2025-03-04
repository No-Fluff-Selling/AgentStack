import re
from typing import List, Optional, Dict, Any, Tuple
from langchain.docstore.document import Document
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from src.types import GraphState
import json
from src.utils.openrouter_client import OpenRouterClient
from src.utils.deepseek_client import DeepseekClient
from src.utils.fireworks_client import FireworksClient
import os
import tiktoken
import re


def execute_rag_process(
    self,
    webpage_docs: List[Document],
    news_docs: List[Document],
    job_docs: List[Document] = None,
    macro_docs: List[Document] = None,
    company_name: str = "",
    key_sections: List[str] = None,
    verification_prompt: str = "",
    report_template: str = "",
    state: GraphState = None,
    branch: str = "",
    query: str = "",
    model: str = "o3-mini",
    user_company_name: str = "",
    user_report: str = ""
) -> Tuple[str, Dict[str, Any]]:
    """Execute the RAG process with improved query generation and verification."""
    try:
        # Initialize optional parameters
        job_docs = job_docs or []
        macro_docs = macro_docs or []
        key_sections = key_sections or []
        
        # Document processing with strict source tracking
        all_docs = []
        source_map = {}  # Maps source URLs to citation numbers
        source_metadata = {}  # Tracks metadata for each source
        source_content = {}  # Stores actual content for each source for verification
        current_source_index = 1

        # After initializing all_docs
        cumulative_tokens = 0
        max_context = self.rag_config['max_cumulative_context']
        response_buffer = self.rag_config['response_token_buffer']

        # Process webpage documents with strict metadata tracking
        for doc in webpage_docs:
            if not doc.page_content.strip():
                continue
            
            source_url = doc.metadata.get("source_url")
            if source_url and source_url not in source_map:
                # Ensure we're using the full specific URL for each webpage, not just the base URL
                source_map[source_url] = current_source_index
                source_metadata[source_url] = {
                    'index': current_source_index,
                    'title': doc.metadata.get('title', 'Webpage'),
                    'type': doc.metadata.get('source_type', 'webpage'),
                    'url': source_url  # Use the specific URL from the metadata
                }
                source_content[source_url] = doc.page_content
                current_source_index += 1
            all_docs.append(doc)

        # Process news documents with strict metadata tracking
        for doc in news_docs:
            if not doc.page_content.strip():
                continue
            
            source_url = doc.metadata.get("source_url")
            if source_url and source_url not in source_map:
                source_map[source_url] = current_source_index
                source_metadata[source_url] = {
                    'index': current_source_index,
                    'title': doc.metadata.get('title', 'News Article'),
                    'type': doc.metadata.get('source_type', 'news'),
                    'url': source_url,
                    'published_date': doc.metadata.get('published_date')
                }
                source_content[source_url] = doc.page_content
                current_source_index += 1
            all_docs.append(doc)
            
        # Process macro trends documents
        for doc in macro_docs:
            if not doc.page_content.strip():
                continue
            
            source_url = doc.metadata.get("source_url")
            if source_url and source_url not in source_map:
                source_map[source_url] = current_source_index
                source_metadata[source_url] = {
                    'index': current_source_index,
                    'title': doc.metadata.get('title', 'Macro Trend'),
                    'type': doc.metadata.get('source_type', 'macro_trend'),
                    'url': source_url,
                    'published_date': doc.metadata.get('published_date')
                }
                source_content[source_url] = doc.page_content
                current_source_index += 1
            all_docs.append(doc)
            
        # Process job listings documents
        for doc in job_docs:
            if not doc.page_content.strip():
                continue
            
            source_url = doc.metadata.get("source_url")
            if source_url and source_url not in source_map:
                source_map[source_url] = current_source_index
                source_metadata[source_url] = {
                    'index': current_source_index,
                    'title': doc.metadata.get('title', 'Job Listing'),
                    'type': doc.metadata.get('source_type', 'job_listing'),
                    'url': source_url
                }
                source_content[source_url] = doc.page_content
                current_source_index += 1
            all_docs.append(doc)

        # Split text into chunks using configuration
        text_splitter = CharacterTextSplitter(
            separator="\n\n",
            chunk_size=int(self.rag_config['context_window'] * self.rag_config['compression_ratio']),
            chunk_overlap=self.rag_config['chunk_overlap']
        )
        chunks = text_splitter.split_documents(all_docs)

        # Create vector store
        embeddings = OpenAIEmbeddings()
        for chunk in chunks:
            self.track_embedding(branch, chunk.page_content)
        vector_store = FAISS.from_documents(chunks, embeddings)
        
        # Store vector store in state
        if 'vector_stores' not in state:
            state['vector_stores'] = {}
        state['vector_stores'][branch] = vector_store

        # Initial RAG process
        # Start with all news and job documents to ensure complete coverage of time-sensitive info
        collected_docs = [
            doc for doc in news_docs + (job_docs or []) 
            if doc.page_content.strip()
        ]
        used_urls = {doc.metadata.get('source_url') for doc in collected_docs if doc.metadata.get('source_url')}
        
        # Use focus areas as initial queries if no key_sections provided
        if not key_sections:
            from src.prompts.target_report_templates import TARGET_FOCUS_AREAS
            key_sections = TARGET_FOCUS_AREAS
            print(f"DEBUG [[execute_rag_process]]: Using {len(key_sections)} focus areas as queries")
        
        total_api_calls = 0
        max_api_calls = self.rag_config['max_iterations'] * self.rag_config['queries_per_batch']

        # Process initial queries
        for query in key_sections:
            if total_api_calls >= max_api_calls:
                break
                
            relevant_docs = vector_store.similarity_search(
                query,
                k=self.rag_config['docs_per_query']
            )
            self.track_tokens(branch, 'text-embedding-ada-002', len(query), 0)
            total_api_calls += 1
            
            for doc in relevant_docs:
                encoder = tiktoken.get_encoding("cl100k_base")
                doc_tokens = len(encoder.encode(doc.page_content))
                if (cumulative_tokens + doc_tokens) > (max_context - response_buffer):
                    break
                cumulative_tokens += doc_tokens
                if doc.metadata['source_url'] not in used_urls:
                    collected_docs.append(doc)
                    used_urls.add(doc.metadata['source_url'])

        # Generate and process adaptive queries if we haven't hit the API limit
        if total_api_calls < max_api_calls:
            adaptive_queries = self.generate_adaptive_queries(collected_docs, self.rag_config['queries_per_batch'], branch, company_name)

            for query in adaptive_queries:
                if total_api_calls >= max_api_calls:
                    break
                    
                new_docs = vector_store.similarity_search(query, k=self.rag_config['docs_per_query'])
                self.track_tokens(branch, 'text-embedding-ada-002', len(query), 0)
                total_api_calls += 1
                
                for doc in new_docs:
                    if doc.metadata['source_url'] not in used_urls:
                        collected_docs.append(doc)
                        used_urls.add(doc.metadata['source_url'])

        # Generate separate contexts for different document types
        macro_context = "\n\n".join([
            f"{d.page_content} [Citation: {source_map[d.metadata['source_url']]}]" 
            for d in collected_docs 
            if d.metadata.get('source_type') == 'macro_trend'
        ])
        
        news_context = "\n\n".join([
            f"{d.page_content} [Citation: {source_map[d.metadata['source_url']]}]" 
            for d in collected_docs 
            if d.metadata.get('source_type') == 'news'
        ])
        
        webpage_context = "\n\n".join([
            f"{d.page_content} [Citation: {source_map[d.metadata['source_url']]}]" 
            for d in collected_docs 
            if d.metadata.get('source_type') == 'webpage'
        ])
        
        job_context = "\n\n".join([
            f"{d.page_content} [Citation: {source_map[d.metadata['source_url']]}]" 
            for d in collected_docs 
            if d.metadata.get('source_type') == 'job_listing'
        ])
        
        # Combined context for backward compatibility
        combined_context = "\n\n".join([
            f"{d.page_content} [Citation: {source_map[d.metadata['source_url']]}]" 
            for d in collected_docs
        ])

        # Create sorted citations list and source overview
        sorted_citations = []
        source_list = []
        
        # Debug the source_metadata
        print(f"DEBUG [[execute_rag_process]]: Source metadata count: {len(source_metadata)}")
        for url, metadata in source_metadata.items():
            print(f"DEBUG [[execute_rag_process]]: Source URL: {url}, Title: {metadata.get('title', 'No Title')}")
        
        for url, metadata in sorted(source_metadata.items(), key=lambda x: x[1]['index']):
            # Full citation for the report - ensure we're using the specific URL
            citation = f"[{metadata['index']}]. [{metadata['title']}]({url}) - {url}"
            if metadata['type'] == 'news':
                citation += f" - News article from {metadata.get('published_date', 'Unknown date')}"
            sorted_citations.append(citation)
            
            # Debug the citation
            print(f"DEBUG [[execute_rag_process]]: Citation {metadata['index']}: {citation}")
            
            # Simplified source listing for the system message
            source_list.append(f'[{metadata["index"]}] {metadata["title"]} ({metadata["type"]})')
        
        citations = "\n".join(sorted_citations)
        sources_overview = "\n".join(source_list)
        
        # Add citation verification to template variables
        template_vars = {
            "combined_context": combined_context,
            "macro_context": macro_context,
            "news_context": news_context,
            "webpage_context": webpage_context,
            "job_context": job_context,
            "company_name": company_name,
            "citations": citations,
            "analysis_date": self.analysis_date,
            "citation_count": len(sorted_citations),
            "user_company_name": user_company_name,
            "current_events_summary": "",  # Default empty string for current events
            "macro_trends_summary": "",  # Default empty string for macro trends
            "industry_statistics": "",  # Default empty string for industry statistics
            "company_offering": "",  # Default empty string for company offering
            "target_market": "",  # Default empty string for target market
            "unique_value_prop": "",  # Default empty string for unique value proposition
            "user_report": user_report,  # User company report for target company analysis
            "hiring_info_context": state["branches"][branch].get("hiring_info", [])
        }
        
        # If verification prompt provided, use it to check for gaps
        if verification_prompt:
            verification_context = "\n\n".join([d.page_content[:200] + "..." for d in collected_docs])
            verification_prompt_with_context = verification_prompt.format(verification_context=verification_context, **template_vars)
            messages = [
                {
                    "role": "developer",
                    "content": "You are a content completeness validator responsible for identifying missing information in business research."
                },
                {
                    "role": "user",
                    "content": verification_prompt_with_context
                }
            ]
            
            missing_sections = self.track_chat_completion(branch, messages)

            # If gaps identified and we haven't hit API limit, try to fill them
            if missing_sections.strip() and missing_sections.strip() != "COMPLETE" and total_api_calls < max_api_calls:
                gap_query = f"Find information about: {missing_sections}"
                verification_docs = vector_store.similarity_search(
                    gap_query,
                    k=self.rag_config['docs_per_query']
                )
                self.track_tokens(branch, 'text-embedding-ada-002', len(gap_query), 0)
                
                for doc in verification_docs:
                    if doc.metadata['source_url'] not in used_urls:
                        collected_docs.append(doc)
                        used_urls.add(doc.metadata['source_url'])

        if branch == "target" and company_name:
            template_vars["company_name"] = company_name

        # Add source verification to the system message
        system_message = f"""Generate factual report about {company_name} using provided sources.
CRITICAL:
- Follow template exactly
- No unsourced claims
- Max context: {max_context//1000}k tokens

Sources:
{sources_overview}"""

        # Before generating the final report:
        MAX_INPUT_TOKENS = self.rag_config['max_cumulative_context']
        encoder = tiktoken.get_encoding("cl100k_base")
        current_tokens = len(encoder.encode(report_template.format(**template_vars)))

        if current_tokens > MAX_INPUT_TOKENS:
            reduction_ratio = MAX_INPUT_TOKENS / current_tokens
            # INLINE TRUNCATION LOGIC
            for key in ['combined_context', 'macro_context', 'news_context', 'webpage_context', 'job_context']:
                if key in template_vars:
                    content = template_vars[key]
                    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', content)
                    keep_count = int(len(sentences) * reduction_ratio)
                    truncated = ' '.join(sentences[:keep_count])
                    
                    # Preserve citations in truncated text
                    truncated = re.sub(r'\[Citation: \d+\]$', '', truncated).strip()
                    if sentences:
                        last_citation = re.findall(r'\[Citation: \d+\]', sentences[-1])
                        if last_citation:
                            truncated += ' ' + last_citation[0]
                    
                    template_vars[key] = truncated
        
        # Generate final report with template variables
        messages = [
            {
                "role": "developer",
                "content": system_message
            },
            {
                "role": "user",
                "content": report_template.format(**template_vars)
            }
        ]
        
        # Save the full prompt to a file
        import os
        from datetime import datetime
        
        # Create output directory if it doesn't exist
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'output')
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate timestamp and filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'prompt_{branch}_{timestamp}.txt'
        filepath = os.path.join(output_dir, filename)
        
        # Write prompt to file
        with open(filepath, 'w') as f:
            f.write("=== DEVELOPER MESSAGE ===\n")
            f.write(messages[0]["content"])
            f.write("\n\n=== USER MESSAGE ===\n")
            f.write(messages[1]["content"])
            f.write("\n=== END PROMPT ===\n")
        
        # Use Deepseek R1 model if specified
        if model == "deepseek-r1":
            try:
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
                            report = deepseek_client.chat_completion(messages, model="deepseek-reasoner")
                            print(f"INFO [[execute_rag_process]]: Used Deepseek R1 model via Deepseek for {branch} report (attempt {attempts+1})")
                            return report, source_metadata
                        except Exception as e:
                            last_error = e
                            attempts += 1
                            print(f"WARNING [[execute_rag_process]]: Error with Deepseek API (attempt {attempts}): {str(e)}")
                            if attempts < max_attempts:
                                print(f"INFO [[execute_rag_process]]: Retrying with Deepseek API...")
                    
                    print(f"WARNING [[execute_rag_process]]: All Deepseek API attempts failed. Last error: {str(last_error)}")
                else:
                    print(f"WARNING [[execute_rag_process]]: Deepseek API key not configured")
                
                # Fall back to Fireworks if Deepseek failed or key not available
                fireworks_api_key = os.getenv("FIREWORKS_API_KEY")
                if fireworks_api_key:
                    try:
                        # Initialize Fireworks client
                        fireworks_client = FireworksClient(api_key=fireworks_api_key)
                        
                        # Get completion from Fireworks
                        report = fireworks_client.chat_completion(messages)
                        print(f"INFO [[execute_rag_process]]: Used Deepseek R1 model via Fireworks.ai as fallback for {branch} report")
                        return report, source_metadata
                    except Exception as e:
                        print(f"ERROR [[execute_rag_process]]: Error with Fireworks.ai fallback: {str(e)}")
                        print("Falling back to default model")
                else:
                    print(f"WARNING [[execute_rag_process]]: Neither Deepseek nor Fireworks API keys configured, falling back to default model")
                
                # Fall back to default model if both Deepseek and Fireworks fail
                report = self.track_chat_completion(branch, messages)
                return report, source_metadata
            except Exception as e:
                print(f"ERROR [[execute_rag_process]]: Error using Deepseek R1 model: {str(e)}")
                print("Falling back to default model")
                report = self.track_chat_completion(branch, messages)
                return report, source_metadata
        else:
            # Use default model via track_chat_completion
            report = self.track_chat_completion(branch, messages)
            return report, source_metadata
        
    except Exception as e:
        print(f"ERROR [[execute_rag_process]]: Error executing RAG process: {str(e)}")
        # Return an error message and empty source metadata in case of exception
        return f"Error generating report: {str(e)}", {}