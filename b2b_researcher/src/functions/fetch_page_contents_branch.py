import agentstack
from typing import Dict, Any, List
from exa_py import Exa
from exa_py.api import Result
from src.types import GraphState, SourceDocument
from langchain.schema import SystemMessage
from src.tools.exa import get_contents
import json
import os
from datetime import datetime, timedelta
import time
import requests
from bs4 import BeautifulSoup

from src.utils.circuit_breaker import with_circuit_breaker, CircuitBreakerConfig
from src.utils.monitoring import with_metrics, StructuredLogger

logger = StructuredLogger(__name__)

# Configure circuit breaker for Exa API
exa_circuit_config = CircuitBreakerConfig(
    failure_threshold=3,    # Open after 3 failures
    reset_timeout=30,       # Try again after 30 seconds
    half_open_calls=2       # Close after 2 successful calls
)

@agentstack.task
@with_circuit_breaker("exa_api", fallback_value=None)
@with_metrics("exa_api")
def fetch_page_contents_branch(self, state: GraphState, branch: str) -> GraphState:
    """Fetch page contents for a branch with circuit breaker and monitoring."""
    logger.info("Starting fetch_page_contents_branch", branch=branch)
    
    try:
        # Get URL from state
        url = state["inputs"].get(f"{branch}_url", "")
        if not url:
            raise ValueError(f"No URL provided for branch {branch}")
        cleaned = url.replace("http://", "").replace("https://", "").replace("www.", "")
        if cleaned.endswith("/"):
            cleaned = cleaned[:-1]

        # Set table name
        table_name = cleaned.replace(".", "_").replace("-", "_").replace("/", "_")
        if "table_name" not in state["branches"][branch]:
            state["branches"][branch]["table_name"] = table_name
        print(f"DEBUG [{branch}] [[fetch_page_contents_branch]]: Using table_name: {table_name}")
        
        # Check if we have cached data
        if self.check_table_exists(table_name):
            print(f"DEBUG [{branch}] [[fetch_page_contents_branch]]: Found cached data for {branch}")
            cached_data = self.get_cached_data(table_name, "url", url)
            if cached_data:
                state["branches"][branch]["page_contents"] = cached_data
                state["branches"][branch]["raw_page_contents"] = cached_data.get("results", [])
                print(f"DEBUG [{branch}] [[fetch_page_contents_branch]]: Successfully loaded cached data for {branch}")
                return state
        
        # If no cached data, proceed with Exa API call
        print(f"DEBUG [{branch}] [[fetch_page_contents_branch]]: No cached data found for {branch}, fetching from Exa")
        
        # Get URLs from state
        urls = state["branches"][branch].get("sitemap_urls", [])
        if not urls:
            print(f"DEBUG [{branch}] [[fetch_page_contents_branch]]: No URLs found in state")
            return state

        print(f"DEBUG [{branch}] [[fetch_page_contents_branch]]: Found {len(urls)} URLs")
        
        # Set up Exa client
        try:
            exa = Exa(api_key=os.getenv("EXA_API_KEY"))
        except Exception as e:
            print(f"DEBUG [{branch}] [[fetch_page_contents_branch]]: Error setting up Exa client: {str(e)}")
            return state
        
        # Process URLs in batches of 100
        batch_size = 100
        all_results = []
        
        for i in range(0, len(urls), batch_size):
            batch_urls = urls[i:i + batch_size]
            logger.info(
                "Processing URL batch",
                branch=branch,
                batch_number=i//batch_size + 1,
                total_batches=(len(urls) + batch_size - 1)//batch_size,
                batch_size=len(batch_urls)
            )
            
            params = {"urls": batch_urls, "text": True}
            start_time = time.time()
            
            try:
                result = get_contents(**params)
                
                # Parse results
                if isinstance(result, str):
                    try:
                        parsed_result = json.loads(result)
                    except Exception as e:
                        logger.error(
                            "Error decoding JSON response",
                            branch=branch,
                            error=str(e),
                            response=result[:1000]  # Log first 1000 chars
                        )
                        parsed_result = {"raw": result}
                else:
                    parsed_result = result
                    
            except requests.exceptions.RequestException as e:
                logger.error(
                    "Exa API request failed",
                    branch=branch,
                    error=str(e),
                    urls=batch_urls
                )
                state["errors"] = state.get("errors", []) + [
                    f"Failed to fetch content for {len(batch_urls)} URLs: {str(e)}"
                ]
                continue
                
            finally:
                latency = time.time() - start_time
                logger.info(
                    "Batch processing complete",
                    branch=branch,
                    latency=latency,
                    urls_processed=len(batch_urls)
                )
                
                # Extract and store results
                content_count = 0
                if hasattr(parsed_result, 'results'):
                    # Ensure each result has the correct URL
                    for result in parsed_result.results:
                        if not hasattr(result, 'url') or not result.url:
                            # If URL is missing, set it to the original URL from batch_urls
                            if hasattr(result, 'id') and result.id in batch_urls:
                                result.url = result.id
                    all_results.extend(parsed_result.results)
                    content_count = len(parsed_result.results)
                    print(f"DEBUG [{branch}] [[fetch_page_contents_branch]]: Added {content_count} results from batch")
                elif isinstance(parsed_result, dict) and 'results' in parsed_result:
                    # Ensure each result has the correct URL
                    for result in parsed_result['results']:
                        if not hasattr(result, 'url') or not result.url:
                            # If URL is missing, set it to the original URL from batch_urls
                            if hasattr(result, 'id') and result.id in batch_urls:
                                result.url = result.id
                    all_results.extend(parsed_result['results'])
                    content_count = len(parsed_result['results'])
                    print(f"DEBUG [{branch}] [[fetch_page_contents_branch]]: Added {content_count} results from batch")
                elif isinstance(parsed_result, list):
                    # Ensure each result has the correct URL
                    for result in parsed_result:
                        if not hasattr(result, 'url') or not result.url:
                            # If URL is missing, set it to the original URL from batch_urls
                            if hasattr(result, 'id') and result.id in batch_urls:
                                result.url = result.id
                    all_results.extend(parsed_result)
                    content_count = len(parsed_result)
                    print(f"DEBUG [{branch}] [[fetch_page_contents_branch]]: Added {content_count} results from batch")
                
                # Track content retrieval per URL
                if content_count > 0:
                    try:
                        # Track text content for each URL only if text parameter was True
                        if params.get('text', False):
                            self.track_exa_usage(branch, 'text', 0, content_count)
                        
                        # If summary was requested
                        if params.get('summary', False):
                            self.track_exa_usage(branch, 'summary', 0, content_count)
                        
                        # If highlight was requested
                        if params.get('highlight', False):
                            self.track_exa_usage(branch, 'highlight', 0, content_count)
                    except Exception as e:
                        print(f"DEBUG [{branch}] [[fetch_page_contents_branch]]: Exception tracking usage: {str(e)}")
                
                time.sleep(0.2)  # Small delay between batches
        
        # Create a results object that matches the expected structure
        results_obj = type('Results', (), {'results': all_results})()
        
        # Store results in state
        if not all_results:
            print(f"DEBUG [{branch}] [[fetch_page_contents_branch]]: No results obtained from any batch")
            state["branches"][branch]["page_contents"] = {}
            state["branches"][branch]["raw_page_contents"] = []
        else:
            print(f"DEBUG [{branch}] [[fetch_page_contents_branch]]: Total pages fetched: {len(all_results)}")
            state["branches"][branch]["page_contents"] = results_obj
            state["branches"][branch]["raw_page_contents"] = all_results
        
        state["messages"].append(SystemMessage(content=f"[{branch}] Fetched {len(all_results)} pages from Exa API"))
        print(f"DEBUG [{branch}] [[fetch_page_contents_branch]]: Finished fetch_page_contents_branch")
        return state

    except Exception as e:
        print(f"ERROR [[fetch_page_contents_branch]]: {str(e)}")
        if "errors" not in state:
            state["errors"] = []
        state["errors"].append(f"Error fetching page contents for {branch}: {str(e)}")
        return state
