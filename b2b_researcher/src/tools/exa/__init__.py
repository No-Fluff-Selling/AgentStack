import os
import sys
from exa_py import Exa
from typing import List, Dict, Optional, Union, Any
import logging
from .retry import retry_on_error

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Check out our docs for more info! https://docs.exa.ai/

API_KEY = os.getenv('EXA_API_KEY')


@retry_on_error(max_retries=10, delay=1.0)
def search_and_contents(
    question: str,
    *,
    type: str = "neural",
    use_autoprompt: bool = True,
    num_results: int = 3,
    highlights: bool = False,
    category: Optional[str] = None,
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
    start_crawl_date: Optional[str] = None,
    end_crawl_date: Optional[str] = None,
    start_published_date: Optional[str] = None,
    end_published_date: Optional[str] = None,
    include_text: Optional[List[str]] = None,
    exclude_text: Optional[List[str]] = None,
    text: bool = False,
    summary: Union[bool, Dict[str, Any]] = False,
    **kwargs
) -> Dict[str, Any]:
    """
    Uses Exa's Python SDK to run semantic search and return a structured response
    containing result highlights and summaries.
    
    Returns a dictionary with keys like "data" where the raw API response is stored.
    """
    logger.debug(f"Initializing Exa with query: {question}")
    exa = Exa(api_key=API_KEY)

    # Build parameters dictionary
    params = {
        "type": type,
        "use_autoprompt": use_autoprompt,
        "num_results": num_results,
        "highlights": highlights,
        "text": text,
        "summary": summary
    }

    # Add optional parameters if provided
    if category:
        params["category"] = category
    if include_domains:
        params["include_domains"] = include_domains
    if exclude_domains:
        params["exclude_domains"] = exclude_domains
    if start_crawl_date:
        params["start_crawl_date"] = start_crawl_date
    if end_crawl_date:
        params["end_crawl_date"] = end_crawl_date
    if start_published_date:
        params["start_published_date"] = start_published_date
    if end_published_date:
        params["end_published_date"] = end_published_date
    if include_text:
        params["include_text"] = include_text
    if exclude_text:
        params["exclude_text"] = exclude_text

    params.update(kwargs)
    logger.debug(f"Calling Exa search_and_contents with parameters: {params}")
    try:
        response = exa.search_and_contents(question, **params)
        logger.debug(f"Received response with {len(response.results)} results")
    except Exception as e:
        logger.error(f"Error calling Exa API: {str(e)}")
        raise
 
    # Instead of concatenating results, return the structured response as a dict.
    result_dict = {
        "autoDate": getattr(response, "autoDate", None),
        "results": [
            {
                "id": eachResult.id,
                "url": eachResult.url,
                "title": eachResult.title,
                "author": getattr(eachResult, "author", ""),
                "publishedDate": getattr(eachResult, "publishedDate", getattr(eachResult, "published_date", "")),
                "text": eachResult.text,
                "summary": eachResult.summary if not highlights else "".join(eachResult.highlights)
            }
            for eachResult in response.results
        ]
    }
    return {"data": result_dict}

@retry_on_error(max_retries=10, delay=1.0)
def search(
    query: str,
    *,
    # Basic search parameters
    num_results: int = 3,
    search_type: str = "auto",
    use_autoprompt: bool = True,
    # Content filtering
    content_type: Optional[str] = None,
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
    include_text: Optional[List[str]] = None,
    exclude_text: Optional[List[str]] = None,
    # Date filtering
    start_crawl_date: Optional[str] = None,
    end_crawl_date: Optional[str] = None,
    start_published_date: Optional[str] = None,
    end_published_date: Optional[str] = None,
    # Content options
    contents: Optional[Dict[str, Any]] = None
) -> str:
    """
    Perform a search using Exa's search endpoint with comprehensive options.
    """
    exa = Exa(api_key=API_KEY)
    
    # Build parameters with proper API field names
    params = {
        "query": query,
        "useAutoprompt": use_autoprompt,
        "type": search_type,
        "category": content_type,
        "numResults": num_results,
        "includeDomains": include_domains,
        "excludeDomains": exclude_domains,
        "includeText": include_text,
        "excludeText": exclude_text,
        "startCrawlDate": start_crawl_date,
        "endCrawlDate": end_crawl_date,
        "startPublishedDate": start_published_date,
        "endPublishedDate": end_published_date,
        "contents": contents #"livecrawl": livecrawl, "livecrawlTimeout": livecrawl_timeout, "subpages": subpages, "subpageTarget": subpage_target
    }
    
    # Clean parameters
    params = {k: v for k, v in params.items() if v is not None}
    
    # Make API call
    response = exa.search(**params)
    
    # Parse results
    parsed_results = []
    for idx, result in enumerate(response.results):
        result_entry = [
            f'<Title id={idx}>{result.title}</Title>',
            f'<URL id={idx}>{result.url}</URL>'
        ]
        if hasattr(result, 'score'):
            result_entry.append(f'<Score id={idx}>{result.score}</Score>')
        if hasattr(result, 'published'):
            result_entry.append(f'<Published id={idx}>{result.published}</Published>')
        if hasattr(result, 'summary'):
            result_entry.append(f'<Summary id={idx}>{result.summary}</Summary>')
        if hasattr(result, 'highlights'):
            result_entry.append(f'<Highlights id={idx}>{"".join(result.highlights)}</Highlights>')
        
        parsed_results.append(''.join(result_entry))
    
    return ''.join(parsed_results)


@retry_on_error(max_retries=10, delay=1.0)
def get_contents(
    urls: Union[str, List[str]],
    *,
    # Content IDs (optional alternative to URLs)
    ids: Optional[List[str]] = None,
    # Content extraction options
    text: bool = True,  # Extract clean text
    # Highlight options
    highlights: Optional[Dict[str, Any]] = None,  # {
        # "numSentences": int,  # Number of sentences per highlight
        # "highlightsPerUrl": int,  # Number of highlights per URL
        # "query": str  # Custom query for highlight selection
    # }
    # Summary options
    summary: Optional[Dict[str, str]] = None,  # {
        # "query": str  # Custom query for summary generation
    # }
    # Crawling options
    livecrawl: str = "fallback",  # "never", "fallback", "always", "auto"
    livecrawl_timeout: Optional[int] = None,  # Timeout in milliseconds
    subpages: Optional[int] = None,  # Number of subpages to crawl
    subpage_target: Optional[str] = None,  # Keyword to find specific subpages
    # Extra content options
    extras: Optional[Dict[str, int]] = None,  # {
        # "links": int,  # Number of links to extract
        # "imageLinks": int  # Number of image links to extract
    # }
) -> str:
    """
    Fetch content from URLs using Exa's contents endpoint with comprehensive options.
    """
    exa = Exa(api_key=API_KEY)
    
    if isinstance(urls, str):
        # Split by comma and clean up each URL
        url_list = [url.strip() for url in urls.split(',') if url.strip()]
    else:
        url_list = urls
    
    # Build parameters
    params = {
        "urls": url_list,
        "text": text
    }
    
    # Add optional parameters if provided
    optional_params = {
        "ids": ids,
        "highlights": highlights,
        "summary": summary,
        "livecrawl": livecrawl,
        "livecrawl_timeout": livecrawl_timeout,
        "subpages": subpages,
        "subpage_target": subpage_target,
        "extras": extras
    }
    
    params.update({k: v for k, v in optional_params.items() if v is not None})
    
    try:
        return exa.get_contents(**params)
    except Exception as e:
        return f"Error fetching contents: {str(e)}\nURLs attempted: {url_list}"
        

@retry_on_error(max_retries=10, delay=1.0)
def find_similar(
    url: str,
    *,
    # Basic parameters
    num_results: int = 3,
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
    # Content filtering
    content_type: Optional[str] = None,  # "company", "research_paper", "news", etc.
    # Text filtering
    include_text: Optional[str] = None,
    exclude_text: Optional[str] = None,
    # Date filtering
    published_after: Optional[str] = None,  # ISO 8601
    published_before: Optional[str] = None,  # ISO 8601
    crawled_after: Optional[str] = None,  # ISO 8601
    crawled_before: Optional[str] = None,  # ISO 8601
    # Result enhancement
    highlights: Optional[Dict[str, Any]] = None,
    summary: Optional[Dict[str, str]] = None,
    extras: Optional[Dict[str, int]] = None
) -> str:
    """
    Find similar links using Exa's findSimilar endpoint with comprehensive options.
    """
    exa = Exa(api_key=API_KEY)
    
    # Build parameters
    params = {
        "url": url,
        "num_results": num_results
    }
    
    # Add optional parameters if provided
    optional_params = {
        "include_domains": include_domains,
        "exclude_domains": exclude_domains,
        "content_type": content_type,
        "include_text": include_text,
        "exclude_text": exclude_text,
        "published_after": published_after,
        "published_before": published_before,
        "crawled_after": crawled_after,
        "crawled_before": crawled_before,
        "highlights": highlights,
        "summary": summary,
        "extras": extras
    }
    
    params.update({k: v for k, v in optional_params.items() if v is not None})
    
    response = exa.find_similar(**params)
    
    parsedResult = ''.join(
        [
            f'<Title id={idx}>{result.title}</Title>'
            f'<URL id={idx}>{result.url}</URL>'
            f'<Score id={idx}>{result.score}</Score>'
            + (f'<Summary id={idx}>{result.summary}</Summary>' if hasattr(result, 'summary') else '')
            + (f'<Highlights id={idx}>{"".join(result.highlights)}</Highlights>' if hasattr(result, 'highlights') else '')
            for (idx, result) in enumerate(response.results)
        ]
    )
    
    return parsedResult


@retry_on_error(max_retries=10, delay=1.0)
def answer(
    question: str,
    *,
    # Context options
    search_results: Optional[List[Dict]] = None,
    urls: Optional[List[str]] = None,
    # Answer customization
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    system_prompt: Optional[str] = None,
    # Search options for automatic context
    num_results: Optional[int] = None,
    content_type: Optional[str] = None,
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
    published_after: Optional[str] = None,
    published_before: Optional[str] = None
) -> str:
    """
    Get an AI-generated answer using Exa's answer endpoint with comprehensive options.
    """
    exa = Exa(api_key=API_KEY)
    
    # Build parameters
    params = {
        "question": question
    }
    
    # Add optional parameters if provided
    optional_params = {
        "search_results": search_results,
        "urls": urls,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system_prompt": system_prompt,
        "num_results": num_results,
        "content_type": content_type,
        "include_domains": include_domains,
        "exclude_domains": exclude_domains,
        "published_after": published_after,
        "published_before": published_before
    }
    
    params.update({k: v for k, v in optional_params.items() if v is not None})
    
    response = exa.answer(**params)
    
    # Format the answer with citations
    answer_text = response.answer
    citations = response.citations if hasattr(response, 'citations') else []
    
    formatted_citations = ''.join(
        [
            f'<Citation id={idx}>'
            f'<Text>{citation.text}</Text>'
            f'<URL>{citation.url}</URL>'
            f'</Citation>'
            for (idx, citation) in enumerate(citations)
        ]
    )
    
    parsedResult = f'<Answer>{answer_text}</Answer>{formatted_citations}'
    
    return parsedResult