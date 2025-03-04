import os
import agentstack
from typing import Dict, Any, List, Optional
from src.types import GraphState
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from urllib.parse import urljoin
import json
from exa_py import Exa

@agentstack.task
def fetch_sitemap_urls_branch(self, state: GraphState, branch: str) -> GraphState:
    """Fetch and analyze sitemap URLs for a branch."""
    url = state["inputs"].get(f"{branch}_url")
    if not url:
        raise ValueError(f"Missing URL for branch {branch}")
    
    print(f"DEBUG [{branch}] [[fetch_sitemap_urls_branch]]: Starting fetch_sitemap_urls_branch with URL: {url}")

    # Clean URL and set table name
    cleaned = url.replace("http://", "").replace("https://", "").replace("www.", "")
    if cleaned.endswith("/"):
        cleaned = cleaned[:-1]
    table_name = cleaned.replace(".", "_").replace("-", "_").replace("/", "_")
    state["branches"][branch]["table_name"] = table_name
    
    # Try common sitemap paths
    sitemap_paths = ['sitemap.xml', 'sitemap_index.xml', 'sitemap/sitemap.xml']
    sitemap_content = None
    sitemap_url = None
    
    for path in sitemap_paths:
        try_url = urljoin(url, path)
        print(f"DEBUG [{branch}] [[fetch_sitemap_urls_branch]]: Trying sitemap at: {try_url}")
        
        response = requests.get(try_url)
        if response.status_code == 200:
            sitemap_content = response.text
            sitemap_url = try_url
            break
    
    if not sitemap_content:
        print(f"Failed to fetch sitemap from {url} (tried paths: {', '.join(sitemap_paths)})")

    if sitemap_content:
    
        # Parse sitemap with BeautifulSoup
        soup = BeautifulSoup(sitemap_content, "xml")
        
        # Check if this is a sitemap index by looking for <sitemapindex> tag
        if soup.find('sitemapindex'):
            # Use GPT-4 to analyze the sitemap index and choose the right sitemap
            sitemaps = [loc.text for loc in soup.find_all("loc")]
            messages = [
                {
                    "role": "developer",
                    "content": "You are an expert at analyzing website sitemaps. Your task is to identify which sitemap in a sitemap index contains the main marketing/public-facing pages of a website."
                },
                {
                    "role": "user",
                    "content": f"""Here are the sitemaps found in the sitemap index:
    {chr(10).join(sitemaps)}

    Analyze these sitemaps and identify which ONE is most likely to contain the main marketing/public-facing pages of the website.
    Consider these factors:
    1. Look for sitemaps that might contain the main pages (e.g., 'main', 'pages', 'marketing', etc.)
    2. Avoid sitemaps that are likely to contain auxiliary content (e.g., 'posts', 'blog', 'products', etc.)
    3. Look for patterns in the URLs that suggest main website content

    Respond with ONLY the full URL of the chosen sitemap."""
                }
            ]
            
            chosen_sitemap = self.track_chat_completion(branch, messages).strip()
            print(f"DEBUG [{branch}] [[fetch_sitemap_urls_branch]]: Chosen sitemap from index: {chosen_sitemap}")
            
            # Fetch the chosen sitemap
            response = requests.get(chosen_sitemap)
            if response.status_code != 200:
                raise ValueError(f"Failed to fetch chosen sitemap: {chosen_sitemap}")
            
            sitemap_content = response.text
            soup = BeautifulSoup(sitemap_content, "xml")
        
        # Extract all URLs from the sitemap
        urls = [loc.text for loc in soup.find_all("loc")]
    else:
        print(f"DEBUG [{branch}] [[fetch_sitemap_urls_branch]]: Failed to fetch sitemap. Using Exa fallback to get links from homepage.")
        try:
            # Fallback: Use Exa to get links from the homepage
            exa = Exa(api_key=os.getenv("EXA_API_KEY"))

            exa_response = exa.get_contents(
                urls=[url],
                text=True,
                livecrawl="always",
                extras={"links": 100}
            )
            
            # Extract URLs from Exa response
            print(f"DEBUG [{branch}] [[fetch_sitemap_urls_branch]]: Exa response: {exa_response}")
            if exa_response:
                urls = []
                response_dict = exa_response.__dict__
                
                if 'results' in response_dict and response_dict['results']:
                    result = response_dict['results'][0]  # Get first result
                    if hasattr(result, 'extras') and 'links' in result.extras:
                        raw_links = result.extras['links']
                        print(f"DEBUG [{branch}] [[fetch_sitemap_urls_branch]]: Raw links: {raw_links}")
                        
                        # Filter out javascript: links and deduplicate URLs
                        filtered_urls = [
                            link for link in raw_links
                            if isinstance(link, str) and link.startswith('http')
                        ]
                        print(f"DEBUG [{branch}] [[fetch_sitemap_urls_branch]]: Filtered links: {filtered_urls}")
                        
                        urls = list(set(filtered_urls))
                        print(f"DEBUG [{branch}] [[fetch_sitemap_urls_branch]]: Deduplicated links: {urls}")
                
                print(f"DEBUG [{branch}] [[fetch_sitemap_urls_branch]]: Found {len(urls)} URLs using Exa fallback")
                
                if not urls:
                    raise ValueError(f"Failed to extract URLs from Exa response for {url}")
            else:
                raise ValueError(f"Failed to get content from Exa for {url}")
                
        except Exception as e:
            print(f"DEBUG [{branch}] [[fetch_sitemap_urls_branch]]: Exa fallback failed with error: {str(e)}")
            raise ValueError(f"Failed to fetch sitemap from {url} and Exa fallback also failed: {str(e)}")

    # Store the complete list of URLs before filtering
    state["branches"][branch]["original_sitemap_urls"] = urls.copy()
    print(f"DEBUG [{branch}] [[fetch_sitemap_urls_branch]]: Stored {len(urls)} original URLs")
    
    # If we have more than 50 URLs, use GPT-4 to select the most relevant ones
    if len(urls) > 50:
        messages = [
            {
                "role": "developer",
                "content": "You are an expert at analyzing website content and determining which pages are most important for understanding a company's value proposition."
            },
            {
                "role": "user",
                "content": f"""Here are the URLs found in the sitemap:
{chr(10).join(urls)}

Analyze these URLs and select NO MORE THAN 50 URLs that are most likely to contain valuable information about the company's value proposition.
Consider these factors:
1. Main pages (homepage, about, features, solutions)
2. Pages that describe products/services
3. Pages with customer success stories or case studies
4. Pages that highlight company differentiators
5. Pages with pricing or packaging information

Respond with ONLY a JSON array of the selected URLs, nothing else."""
            }
        ]
        
        selected_urls = json.loads(self.track_chat_completion(branch, messages))
        print(f"DEBUG [{branch}] [[fetch_sitemap_urls_branch]]: Selected {len(selected_urls)} URLs from {len(urls)} total")
        urls = selected_urls
    
    state["branches"][branch]["sitemap_urls"] = urls
    print(f"DEBUG [{branch}] [[fetch_sitemap_urls_branch]]: Finished fetch_sitemap_urls_branch. Found {len(urls)} URLs")
    return state