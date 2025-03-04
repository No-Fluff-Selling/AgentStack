import os
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup

def fetch_sitemap_urls(url_to_fetch: str) -> str:
    """
    Fetch a sitemap from a given URL and return all URLs as a comma-separated string.
    Args:
        url_to_fetch: The URL of the sitemap to fetch
    Returns:
        Comma-separated string of all URLs in the sitemap
    """
    # Try common sitemap paths
    sitemap_paths = ['sitemap.xml', 'sitemap_index.xml', 'sitemap/sitemap.xml']
    
    for path in sitemap_paths:
        sitemap_url = urljoin(url_to_fetch, path)
        print(f"Trying sitemap at: {sitemap_url}")  # Debug print
        
        response = requests.get(sitemap_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "xml")
            urls = [loc.text for loc in soup.find_all("loc")]
            if urls:
                return ",".join(urls)
    
    return f"Failed to fetch sitemap from {url_to_fetch} (tried paths: {', '.join(sitemap_paths)})"