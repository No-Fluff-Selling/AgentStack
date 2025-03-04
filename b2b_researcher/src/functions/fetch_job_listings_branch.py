import os
import re
import agentstack
import requests
import logging
import json
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional, Tuple, Set
from src.types import GraphState
from exa_py import Exa
from datetime import datetime
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Job board configuration
JOB_BOARD_CONFIG = {
    'ashby': {
        'name': 'Ashby',
        'patterns': ['ashby_embed', 'jobs.ashbyhq.com', 'ashbyhq.com/embed'],
        'url_template': 'https://jobs.ashbyhq.com/{company}',
        'api_template': 'https://api.ashbyhq.com/posting-api/job-board/{company}',
        'company_regex': r'jobs\.ashbyhq\.com/([^/"\']+)',
        'job_url_pattern': r'jobs\.ashbyhq\.com/[^/]+/[a-zA-Z0-9-]+',
        'use_api': True
    },
    'greenhouse': {
        'name': 'Greenhouse',
        'patterns': ['greenhouse.io', 'boards.greenhouse.io', 'data-gh-src', 'data-gh-board'],
        'url_template': 'https://boards.greenhouse.io/{company}',
        'api_template': 'https://boards-api.greenhouse.io/v1/boards/{company}/jobs',
        'company_regex': r'boards\.greenhouse\.io/(?:embed/)?([^/"\']+)',
        'job_url_pattern': r'boards\.greenhouse\.io/[^/]+/jobs/\d+',
        'use_api': True
    },
    'lever': {
        'name': 'Lever',
        'patterns': ['jobs.lever.co', 'lever-jobs.js', 'data-lever-src'],
        'url_template': 'https://jobs.lever.co/{company}',
        'api_template': None,
        'company_regex': r'jobs\.lever\.co/([^/"\']+)',
        'job_url_pattern': r'jobs\.lever\.co/[^/]+/[a-zA-Z0-9-]+',
        'use_api': False
    },
    'workday': {
        'name': 'Workday',
        'patterns': ['workday.com', 'myworkdayjobs.com'],
        'url_template': 'https://company.wd5.myworkdayjobs.com/en-US/{company}Careers',
        'api_template': None,
        'company_regex': r'https?://([^.]+)\.workday\.com/[^/"\']+',
        'job_url_pattern': r'myworkdayjobs\.com/[^/]+/job/[^/]+/[^/]+',
        'use_api': False
    },
    'bamboohr': {
        'name': 'BambooHR',
        'patterns': ['bamboohr.com'],
        'url_template': 'https://{company}.bamboohr.com/jobs/',
        'api_template': None,
        'company_regex': r'https?://([^.]+)\.bamboohr\.com',
        'job_url_pattern': r'bamboohr\.com/jobs/view\.php',
        'use_api': False
    },
    'jobvite': {
        'name': 'Jobvite',
        'patterns': ['jobvite.com'],
        'url_template': 'https://jobs.jobvite.com/{company}/jobs',
        'api_template': None,
        'company_regex': r'jobs\.jobvite\.com/([^/"\']+)',
        'job_url_pattern': r'jobs\.jobvite\.com/[^/]+/job/[^/]+',
        'use_api': False
    },
    'smartrecruiters': {
        'name': 'SmartRecruiters',
        'patterns': ['smartrecruiters.com'],
        'url_template': 'https://jobs.smartrecruiters.com/{company}',
        'api_template': None,
        'company_regex': r'jobs\.smartrecruiters\.com/([^/"\']+)',
        'job_url_pattern': r'jobs\.smartrecruiters\.com/[^/]+/[^/]+',
        'use_api': False
    },
    'recruitee': {
        'name': 'Recruitee',
        'patterns': ['recruitee.com'],
        'url_template': 'https://{company}.recruitee.com/',
        'api_template': None,
        'company_regex': r'([^/"\']+)\.recruitee\.com',
        'job_url_pattern': r'recruitee\.com/o/[^/]+',
        'use_api': False
    },
    'recruiterbox': {
        'name': 'RecruiterBox',
        'patterns': ['recruiterbox.com'],
        'url_template': 'https://{company}.recruiterbox.com/jobs',
        'api_template': None,
        'company_regex': r'([^/"\']+)\.recruiterbox\.com',
        'job_url_pattern': r'recruiterbox\.com/jobs/[^/]+',
        'use_api': False
    },
    'taleo': {
        'name': 'Taleo',
        'patterns': ['taleo.net', 'tbe.taleo.net'],
        'url_template': 'https://{company}.taleo.net/careersection/',
        'api_template': None,
        'company_regex': r'https?://([^.]+)\.taleo\.net',
        'job_url_pattern': r'taleo\.net/careersection/[^/]+/jobdetail',
        'use_api': False
    },
    'successfactors': {
        'name': 'SuccessFactors',
        'patterns': ['successfactors.com', 'careers.successfactors.com', 'jobs.successfactors.com'],
        'url_template': 'https://career{company}.sap.com/careers',
        'api_template': None,
        'company_regex': r'career([^.]+)\.sap\.com|([^.]+)\.jobs\.successfactors\.com',
        'job_url_pattern': r'successfactors\.com/[^/]+/job/[^/]+',
        'use_api': False
    },
    'icims': {
        'name': 'iCIMS',
        'patterns': ['icims.com', 'jobs.icims.com'],
        'url_template': 'https://jobs-{company}.icims.com/jobs/search',
        'api_template': None,
        'company_regex': r'jobs-([^.]+)\.icims\.com',
        'job_url_pattern': r'icims\.com/jobs/\d+/',
        'use_api': False
    },
    'breezy': {
        'name': 'Breezy HR',
        'patterns': ['breezy.hr'],
        'url_template': 'https://{company}.breezy.hr/',
        'api_template': None,
        'company_regex': r'([^.]+)\.breezy\.hr',
        'job_url_pattern': r'breezy\.hr/p/[^/]+',
        'use_api': False
    },
    'applytojob': {
        'name': 'ApplyToJob',
        'patterns': ['applytojob.com'],
        'url_template': 'https://{company}.applytojob.com/apply/',
        'api_template': None,
        'company_regex': r'([^.]+)\.applytojob\.com',
        'job_url_pattern': r'applytojob\.com/apply/[^/]+',
        'use_api': False
    },
    'myworkdayjobs': {
        'name': 'MyWorkdayJobs',
        'patterns': ['myworkdayjobs.com'],
        'url_template': 'https://{company}.wd5.myworkdayjobs.com/en-US/{company}Careers',
        'api_template': None,
        'company_regex': r'([^.]+)\.wd\d+\.myworkdayjobs\.com',
        'job_url_pattern': r'myworkdayjobs\.com/[^/]+/job/',
        'use_api': False
    },
    'paylocity': {
        'name': 'Paylocity',
        'patterns': ['paylocity.com', 'recruiting.paylocity.com'],
        'url_template': 'https://recruiting.paylocity.com/recruiting/jobs/All/{company}',
        'api_template': None,
        'company_regex': r'jobs/All/([^/]+)',
        'job_url_pattern': r'paylocity\.com/recruiting/jobs/Details/\d+',
        'use_api': False
    },
    'teamtailor': {
        'name': 'TeamTailor',
        'patterns': ['teamtailor.com'],
        'url_template': 'https://{company}.teamtailor.com/jobs',
        'api_template': None,
        'company_regex': r'([^.]+)\.teamtailor\.com',
        'job_url_pattern': r'teamtailor\.com/jobs/[^/]+',
        'use_api': False
    },
    'workable': {
        'name': 'Workable',
        'patterns': ['workable.com', 'apply.workable.com'],
        'url_template': 'https://apply.workable.com/{company}/',
        'api_template': None,
        'company_regex': r'apply\.workable\.com/([^/]+)',
        'job_url_pattern': r'workable\.com/j/[A-Z0-9]+',
        'use_api': False
    },
    'jazzhr': {
        'name': 'JazzHR',
        'patterns': ['jazzhr.com', 'app.jazz.co'],
        'url_template': 'https://{company}.applytojob.com/apply/',
        'api_template': None,
        'company_regex': r'([^.]+)\.applytojob\.com',
        'job_url_pattern': r'applytojob\.com/apply/[^/]+',
        'use_api': False
    },
    'jobleads': {
        'name': 'JobLeads',
        'patterns': ['jobleads.com'],
        'url_template': 'https://{company}.jobleads.com/jobs',
        'api_template': None,
        'company_regex': r'([^.]+)\.jobleads\.com',
        'job_url_pattern': r'jobleads\.com/jobs/[^/]+',
        'use_api': False
    }
}


class JobListingFetcher:
    """A class to handle fetching job listings and hiring info from company websites."""
    
    def __init__(self, branch: str, state: GraphState, exa_client: Exa):
        """Initialize the JobListingFetcher with required parameters."""
        self.branch = branch
        self.state = state
        self.exa = exa_client
        self.company_url = state["inputs"].get(f"{branch}_url", "")
        self.domain_info = self._get_domain_info(self.company_url)
        self.company_name = self.domain_info["company_name"]
        self.main_domain = self.domain_info["main_domain"]
        self.job_listings = []
        self.hiring_info = []
        self.MAX_JOB_LISTINGS = 25
        
    def _log(self, level: str, message: str):
        """Helper method to log messages with branch information."""
        msg = f"[{self.branch}] {message}"
        if level == "debug":
            logger.debug(msg)
        elif level == "info":
            logger.info(msg)
        elif level == "warning":
            logger.warning(msg)
        elif level == "error":
            logger.error(msg)
        else:
            print(msg)
    
    def _get_domain_info(self, url: str) -> Dict[str, str]:
        """Extract domain and company name from URL."""
        if not url:
            return {"main_domain": "", "company_name": ""}
            
        parsed_url = urlparse(url)
        domain_parts = parsed_url.netloc.split('.')
        
        # Get the main domain and company name
        if len(domain_parts) >= 2:
            if domain_parts[0] == 'www':
                # For www.example.com, get example.com
                main_domain = '.'.join(domain_parts[1:])
                company_name = domain_parts[1]
            else:
                # For example.com, get example.com
                main_domain = '.'.join(domain_parts)
                company_name = domain_parts[0]
        else:
            main_domain = parsed_url.netloc
            company_name = domain_parts[0]
            
        return {
            "main_domain": main_domain, 
            "company_name": company_name
        }

    def _extract_content_from_response(self, response):
        """Extract text content from Exa response."""
        try:
            # Handle SearchResponse objects from exa_py.api
            from exa_py.api import SearchResponse
            if isinstance(response, SearchResponse):
                self._log("debug", f"Processing Exa SearchResponse object")
                
                # Access the results directly from the SearchResponse object
                if hasattr(response, 'results') and response.results:
                    first_result = response.results[0]
                    
                    # Try to get the text content
                    if hasattr(first_result, 'text') and first_result.text:
                        content = first_result.text
                        self._log("info", f"Successfully extracted content from Exa SearchResponse (length: {len(content)})")
                        return content
                    
                    # Try to get HTML content if text isn't available
                    if hasattr(first_result, 'html') and first_result.html:
                        content = first_result.html
                        self._log("info", f"Using HTML content from Exa SearchResponse (length: {len(content)})")
                        return content
                        
                    # Check what attributes are available
                    available_attrs = [attr for attr in dir(first_result) if not attr.startswith('_')]
                    self._log("warning", f"Exa result missing 'text' field. Available attributes: {available_attrs}")
                else:
                    self._log("warning", f"No results found in Exa SearchResponse")
                return ""
                
            # Handle dictionary responses
            elif isinstance(response, dict):
                results = response.get("results", [])
                if not results and "data" in response:
                    # Handle nested data structure
                    results = response.get("data", {}).get("results", [])
                
                self._log("debug", f"Exa API response structure: {list(response.keys())}")
                
                if results and len(results) > 0:
                    # Check if the first result has text content
                    if "text" in results[0]:
                        content = results[0].get("text", "")
                        self._log("info", f"Successfully extracted content from Exa (length: {len(content)})")
                        return content
                    else:
                        self._log("warning", f"Exa result missing 'text' field. Available fields: {list(results[0].keys())}")
                else:
                    self._log("warning", f"No results found in Exa response. Response structure: {response.keys()}")
            else:
                self._log("warning", f"Unexpected Exa response type: {type(response)}")
            return ""
        except Exception as e:
            self._log("warning", f"Failed to extract text from Exa response: {str(e)}")
            return ""

    def _extract_links_from_response(self, response_text: str) -> List[str]:
        """Extract links from Exa response."""
        links = []
        links_match = re.search(r".*?'links': \[(.*?)\]", str(response_text), re.DOTALL)
        if links_match:
            links = [link.strip().strip("'\"") for link in links_match.group(1).split(',') if link.strip()]
        return links

    def _normalize_links(self, links: List[str], base_url: str) -> List[str]:
        """Normalize relative links to absolute URLs."""
        normalized = []
        for link in links:
            if link.startswith('/'):
                normalized.append(f"{base_url.rstrip('/')}{link}")
            elif link.startswith('http'):
                normalized.append(link)
            else:
                normalized.append(f"{base_url.rstrip('/')}/{link.lstrip('/')}")
        return list(set(normalized))  # Remove duplicates

    def _fetch_url_content(self, url: str, timeout: int = 30) -> str:
        """Fetch content from a URL using Exa."""
        try:
            self._log("info", f"Fetching content from {url} using Exa")
            
            # Try using the search API first which often works better
            try:
                search_response = self.exa.search(
                    query=f"site:{url}",
                    use_autoprompt=False,
                    num_results=1,
                    include_domains=[url],
                    exclude_domains=[],
                    start_published_date=None,
                    end_published_date=None,
                    text=True,
                    highlights=False,
                    summarize=False
                )
                
                # Extract content from search response
                content = self._extract_content_from_response(search_response)
                if content:
                    self._log("info", f"Successfully fetched content using Exa search API")
                    return content
            except Exception as e:
                self._log("warning", f"Exa search API failed: {str(e)}. Falling back to get_contents.")
            
            # Fall back to get_contents if search fails
            exa_response = self.exa.get_contents(
                urls=[url],
                text=True,
                livecrawl="always",
                max_wait_ms=30000,  # Increase wait time to 30 seconds
                num_retries=2       # Add retries
            )
            
            # Extract content from Exa response
            content = self._extract_content_from_response(exa_response)
            if content:
                return content
                
            # Try to extract raw HTML if text extraction failed
            if isinstance(exa_response, dict) and "results" in exa_response:
                results = exa_response.get("results", [])
                if results and len(results) > 0 and "raw_html" in results[0]:
                    raw_html = results[0].get("raw_html", "")
                    if raw_html:
                        self._log("info", f"Using raw HTML from Exa (length: {len(raw_html)})")
                        return raw_html
            
            # Fallback to direct request only if Exa fails
            self._log("warning", "Exa returned no content, falling back to direct request")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.text
            
        except Exception as e:
            self._log("error", f"Failed to fetch content: {str(e)}")
            return ""

    def _detect_job_boards(self, html_content: str) -> List[str]:
        """Detect job board integrations in HTML content."""
        detected_boards = []
        
        # Pattern-based detection
        for board, config in JOB_BOARD_CONFIG.items():
            for pattern in config['patterns']:
                if re.search(pattern, html_content, re.IGNORECASE):
                    self._log("info", f"Detected {config['name']} job board via pattern: {pattern}")
                    detected_boards.append(board)
                    break
        
        # URL-based detection
        url_patterns = [
            (r'taleo\.net/careersection', 'taleo'),
            (r'successfactors\.com/careers', 'successfactors'),
            (r'jobs\.icims\.com', 'icims'),
            (r'breezy\.hr', 'breezy'),
            (r'applytojob\.com/apply', 'applytojob'),
            (r'myworkdayjobs\.com', 'myworkdayjobs'),
            (r'recruiting\.paylocity\.com', 'paylocity'),
            (r'teamtailor\.com/jobs', 'teamtailor'),
            (r'apply\.workable\.com', 'workable'),
            (r'jobs\.lever\.co', 'lever'),
            (r'boards\.greenhouse\.io', 'greenhouse'),
            (r'jazz\.co', 'jazzhr'),
            (r'jobleads\.com', 'jobleads')
        ]
        
        for pattern, board_key in url_patterns:
            if board_key not in detected_boards and re.search(pattern, html_content, re.IGNORECASE):
                self._log("info", f"Detected {JOB_BOARD_CONFIG[board_key]['name']} job board via URL pattern")
                detected_boards.append(board_key)
        
        # Script-based detection for ATS integrations
        script_patterns = [
            (r'src=["\'](https?://[^"\']*taleo\.net[^"\']*)["\']', 'taleo'),
            (r'src=["\'](https?://[^"\']*successfactors\.com[^"\']*)["\']', 'successfactors'),
            (r'src=["\'](https?://[^"\']*icims\.com[^"\']*)["\']', 'icims'),
            (r'src=["\'](https?://[^"\']*breezy\.hr[^"\']*)["\']', 'breezy'),
            (r'src=["\'](https?://[^"\']*applytojob\.com[^"\']*)["\']', 'applytojob'),
            (r'src=["\'](https?://[^"\']*myworkdayjobs\.com[^"\']*)["\']', 'myworkdayjobs'),
            (r'src=["\'](https?://[^"\']*paylocity\.com[^"\']*)["\']', 'paylocity'),
            (r'src=["\'](https?://[^"\']*teamtailor\.com[^"\']*)["\']', 'teamtailor'),
            (r'src=["\'](https?://[^"\']*workable\.com[^"\']*)["\']', 'workable'),
            (r'src=["\'](https?://[^"\']*ashbyhq\.com[^"\']*)["\']', 'ashby'),
            (r'src=["\'](https?://[^"\']*bamboohr\.com[^"\']*)["\']', 'bamboohr'),
            (r'src=["\'](https?://[^"\']*jobvite\.com[^"\']*)["\']', 'jobvite'),
            (r'src=["\'](https?://[^"\']*smartrecruiters\.com[^"\']*)["\']', 'smartrecruiters'),
            (r'src=["\'](https?://[^"\']*recruitee\.com[^"\']*)["\']', 'recruitee'),
            (r'src=["\'](https?://[^"\']*recruiterbox\.com[^"\']*)["\']', 'recruiterbox'),
            (r'src=["\'](https?://[^"\']*lever\.co[^"\']*)["\']', 'lever'),
            (r'src=["\'](https?://[^"\']*greenhouse\.io[^"\']*)["\']', 'greenhouse'),
            (r'src=["\'](https?://[^"\']*jazz\.co[^"\']*)["\']', 'jazzhr'),
            (r'src=["\'](https?://[^"\']*jobleads\.com[^"\']*)["\']', 'jobleads')
        ]
        
        for pattern, board_key in script_patterns:
            if board_key not in detected_boards and re.search(pattern, html_content, re.IGNORECASE):
                self._log("info", f"Detected {JOB_BOARD_CONFIG[board_key]['name']} job board via script URL")
                detected_boards.append(board_key)
        
        return detected_boards

    def _extract_hiring_info(self, content_text: str, page_url: str, source_type: str = "general") -> Optional[Dict[str, Any]]:
        """Extract hiring information from page content."""
        
        print(f"Raw page content: {content_text}")
            
        hiring_messages = [
            {
                "role": "developer",
                "content": "You are a job information analyst. Your task is to extract key hiring information from a company's careers page."
            },
            {
                "role": "user",
                "content": f"""Analyze this content from a {'careers/jobs' if source_type != 'general' else ''} page and extract key hiring information.
                
Focus on:
1. General hiring statements (e.g., "We're always looking for talented individuals")
2. Current hiring status (e.g., "We currently have 15 open positions")
3. Key departments or areas hiring
4. Application process information
5. Hiring priorities or focus areas
6. Any other relevant hiring information

Content to analyze:
{content_text}

Provide your analysis as plaintext without any JSON structure.
"""
            }
        ]
        
        hiring_info_result = self.track_chat_completion(hiring_messages)

        print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        print("Hiring info analysis messages:", hiring_info_result)
        print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        
        return {
            "url": page_url,
            "analysis": hiring_info_result,
            "source_type": source_type,
            "extracted_at": datetime.now().isoformat()
        }

    def _analyze_urls_for_job_listings(self, urls: List[str], context: str = "general") -> List[str]:
        """Use LLM to identify job listing URLs from a list of URLs."""
        if not urls:
            return []
            
        context_prompts = {
            "general": "You are a job listing analyst. Your task is to identify job listing URLs.",
            "ashby": "You are a job listing analyst specializing in Ashby job board URLs.",
            "greenhouse": "You are a job listing analyst specializing in Greenhouse job board URLs.",
            "lever": "You are a job listing analyst specializing in Lever job board URLs.",
            "workday": "You are a job listing analyst specializing in Workday job board URLs.",
            "bamboohr": "You are a job listing analyst specializing in BambooHR job board URLs.",
            "jobvite": "You are a job listing analyst specializing in Jobvite job board URLs.",
            "smartrecruiters": "You are a job listing analyst specializing in SmartRecruiters job board URLs.",
            "recruitee": "You are a job listing analyst specializing in Recruitee job board URLs.",
            "recruiterbox": "You are a job listing analyst specializing in RecruiterBox job board URLs.",
            "taleo": "You are a job listing analyst specializing in Taleo job board URLs.",
            "successfactors": "You are a job listing analyst specializing in SuccessFactors job board URLs.",
            "icims": "You are a job listing analyst specializing in iCIMS job board URLs.",
            "breezy": "You are a job listing analyst specializing in Breezy HR job board URLs.",
            "applytojob": "You are a job listing analyst specializing in ApplyToJob job board URLs.",
            "myworkdayjobs": "You are a job listing analyst specializing in MyWorkdayJobs job board URLs.",
            "paylocity": "You are a job listing analyst specializing in Paylocity job board URLs.",
            "teamtailor": "You are a job listing analyst specializing in TeamTailor job board URLs.",
            "workable": "You are a job listing analyst specializing in Workable job board URLs.",
            "jazzhr": "You are a job listing analyst specializing in JazzHR job board URLs.",
            "jobleads": "You are a job listing analyst specializing in JobLeads job board URLs.",
            "career_page": "You are a job listing analyst specialized in identifying job URLs from HTML content."
        }
        
        # Default to general context if not specified
        context_key = context if context in context_prompts else "general"
        
        context_specific_instructions = {
            "ashby": "Ashby job listing URLs typically follow this pattern: https://jobs.ashbyhq.com/[company]/[job-id]",
            "greenhouse": "Greenhouse job listing URLs typically contain '/jobs/' and a numeric ID or a job title slug.",
            "lever": "Lever job listing URLs typically follow this pattern: https://jobs.lever.co/[company]/[job-id] and often include job titles.",
            "workday": "Workday job listing URLs typically contain '/job/' and some form of ID.",
            "bamboohr": "BambooHR job listing URLs typically contain '/jobs/' followed by a job ID or title.",
            "jobvite": "Jobvite job listing URLs typically contain '/job/' and a job ID.",
            "smartrecruiters": "SmartRecruiters job listing URLs typically have a company name followed by job titles and IDs.",
            "recruitee": "Recruitee job listing URLs typically contain 'o=' followed by a job slug or ID.",
            "recruiterbox": "RecruiterBox job listing URLs typically contain '/jobs/' followed by a job ID or title.",
            "taleo": "Taleo job listing URLs typically contain 'careersection' and 'jobdetail' segments.",
            "successfactors": "SuccessFactors job listing URLs typically contain '/job/' and a numeric or alpha ID.",
            "icims": "iCIMS job listing URLs typically contain '/jobs/' followed by a numeric ID.",
            "breezy": "Breezy HR job listing URLs typically contain '/p/' followed by a job ID or slug.",
            "applytojob": "ApplyToJob URLs typically contain '/apply/' followed by a job ID or slug.",
            "myworkdayjobs": "MyWorkdayJobs URLs typically contain '/job/' in the path.",
            "paylocity": "Paylocity job listing URLs typically contain '/Details/' followed by a numeric ID.",
            "teamtailor": "TeamTailor job listing URLs typically contain '/jobs/' followed by a job slug.",
            "workable": "Workable job listing URLs typically contain '/j/' followed by an ID with capital letters and numbers.",
            "jazzhr": "JazzHR job listing URLs typically use applytojob.com with '/apply/' followed by a job ID.",
            "jobleads": "JobLeads job listing URLs typically contain '/jobs/' followed by a job ID or title.",
            "career_page": "Consider URL patterns that suggest job listings (e.g., numeric IDs, job titles, position names).\nPay special attention to URLs that might come from job board platforms."
        }
        
        # Limit number of URLs to analyze to avoid token limits
        urls_to_analyze = urls[:200]
        
        instructions = context_specific_instructions.get(context_key, "Consider URL patterns that suggest job listings (e.g., numeric IDs, job titles, position names).")
        
        messages = [
            {
                "role": "developer",
                "content": context_prompts[context_key]
            },
            {
                "role": "user",
                "content": f"""Analyze these URLs and identify which ones are individual job listing pages.
                
{instructions}

URLs to analyze:
{chr(10).join(urls_to_analyze)}

**IMPORTANT: Respond ONLY with a JSON array of URLs that are definitely job listing pages."""
            }
        ]
        
        job_urls_result = self.track_chat_completion(messages)
        
        try:
            job_urls = json.loads(job_urls_result)
            return job_urls if isinstance(job_urls, list) else []
        except json.JSONDecodeError as e:
            self._log("error", f"Failed to parse job URLs from LLM: {e}")
            return []

    def _score_career_page_content(self, content: str, url: str) -> int:
        """
        Score the relevance of a career page based on its content.
        Returns a score from 0-100, with higher scores indicating better career pages.
        """
        score = 0
        
        # Check for career-related keywords in the content
        career_keywords = [
            'careers', 'jobs', 'positions', 'openings', 'opportunities', 'join our team',
            'apply now', 'current openings', 'job description', 'open positions',
            'hiring', 'job listing', 'employment', 'work with us', 'vacancy', 'vacancies',
            'job posting', 'career opportunities', 'job applications', 'job search'
        ]
        
        # Score based on keywords - higher weights for more specific keywords
        for keyword in career_keywords:
            keyword_count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', content.lower()))
            if keyword_count > 0:
                # Increase score based on keyword relevance
                if keyword in ['careers', 'jobs', 'positions', 'openings', 'hiring']:
                    score += min(20, keyword_count * 5)  # Cap at 20 points per keyword
                else:
                    score += min(10, keyword_count * 2)  # Cap at 10 points per keyword
        
        # Bonus for URLs with career-related terms
        career_url_indicators = ['careers', 'jobs', 'career', 'job', 'employment', 'work', 'join']
        for indicator in career_url_indicators:
            if indicator in url.lower():
                score += 15
                break  # Only apply this bonus once
        
        # Bonus for subdomains like careers.domain.com
        if re.match(r'https?://(?:careers|jobs)\.', url.lower()):
            score += 25
        
        # Bonus for content length - more comprehensive career pages tend to be longer
        if len(content) > 5000:
            score += 10
        elif len(content) > 2000:
            score += 5
        
        # Check for number/count patterns that might indicate job counts
        job_count_patterns = [
            r'\b(\d+)\s+(?:open|current)?\s*(?:positions|jobs|openings|opportunities|vacancies)\b',
            r'\b(?:over|more than)\s+(\d+)\s+(?:positions|jobs|openings|opportunities|vacancies)\b',
            r'\b(?:we have|we\'re hiring for|we are hiring for)\s+(\d+)\s+(?:positions|jobs|roles)\b'
        ]
        
        for pattern in job_count_patterns:
            if re.search(pattern, content.lower()):
                score += 20  # High value for content that quantifies job openings
                break  # Only apply this bonus once
        
        # Check for job board integration indicators
        job_board_indicators = [
            'greenhouse.io', 'lever.co', 'workday', 'taleo', 'successfactors',
            'icims', 'jobvite', 'smartrecruiters', 'bamboohr', 'applytojob',
            'recruiterbox', 'recruitee', 'breezy.hr', 'workable', 'teamtailor'
        ]
        
        for indicator in job_board_indicators:
            if indicator in content.lower():
                score += 15
                break  # Only apply this bonus once
        
        # Cap the maximum score at 100
        return min(100, score)

    def _fetch_job_listings(self, urls: List[str]) -> List[Dict[str, str]]:
        """Fetch job listings from a list of URLs."""
        if not urls:
            return []
            
        # Limit to MAX_JOB_LISTINGS
        urls_to_fetch = urls[:self.MAX_JOB_LISTINGS]
        
        try:
            self._log("info", f"Fetching {len(urls_to_fetch)} job listings")
            listings_content = self.exa.get_contents(
                urls=urls_to_fetch,
                text=True,
                livecrawl="always"
            )
            
            # Parse the results
            url_matches = re.finditer(r'<URL id=(\d+)>(.*?)</URL>', str(listings_content))
            content_matches = re.finditer(r'<Content id=(\d+)>(.*?)</Content>', str(listings_content))
            summary_matches = re.finditer(r'<Summary id=(\d+)>(.*?)</Summary>', str(listings_content))
            
            url_dict = {m.group(1): m.group(2) for m in url_matches}
            content_dict = {m.group(1): m.group(2) for m in content_matches}
            summary_dict = {m.group(1): m.group(2) for m in summary_matches}
            
            # Create job listings
            result_listings = []
            for idx in url_dict.keys():
                result_listings.append({
                    "url": url_dict.get(idx),
                    "text": content_dict.get(idx, ""),
                    "summary": summary_dict.get(idx, "")
                })
                
            return result_listings
        except Exception as e:
            self._log("error", f"Error fetching job listings: {e}")
            return []

    def track_chat_completion(self, messages) -> str:
        """Wrapper for self.track_chat_completion to maintain compatibility."""
        # Assuming this method is already defined elsewhere in your codebase
        if not isinstance(self, JobListingFetcher):
            return self.track_chat_completion(self.branch, messages)
        return self.state.get("track_chat_completion", lambda *args: "")(self.branch, messages)

    def _process_job_board(self, board_key: str, html_content: str) -> Tuple[List[Dict[str, str]], List[Dict[str, Any]]]:
        """Process a specific job board for job listings and hiring info."""
        job_listings = []
        hiring_info = []
        
        board_config = JOB_BOARD_CONFIG.get(board_key)
        if not board_config:
            self._log("warning", f"No configuration found for job board: {board_key}")
            return job_listings, hiring_info
            
        self._log("info", f"Processing {board_config['name']} job board")
        
        # Extract company name from HTML using regex if available
        company_id = self.company_name.lower()
        if board_config['company_regex'] and html_content:
            regex_match = re.search(board_config['company_regex'], html_content)
            if regex_match:
                company_id = regex_match.group(1)
                self._log("info", f"Found {board_config['name']} company ID: {company_id}")
        
        # Try API first if available
        if board_config['use_api'] and board_config['api_template']:
            api_url = board_config['api_template'].format(company=company_id)
            self._log("info", f"Trying {board_config['name']} API: {api_url}")
            
            try:
                api_response = requests.get(api_url, headers={
                    'Accept': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                })
                
                if api_response.status_code == 200:
                    try:
                        api_data = api_response.json()
                        
                        # Process API data based on job board type
                        if board_key == 'ashby':
                            job_listings, hiring_info = self._process_ashby_api(api_data, company_id, api_url)
                        elif board_key == 'greenhouse':
                            job_listings, hiring_info = self._process_greenhouse_api(api_data, company_id, api_url)
                        
                        if job_listings:
                            self._log("info", f"Successfully found {len(job_listings)} job listings from {board_config['name']} API")
                            return job_listings, hiring_info
                    except Exception as json_err:
                        self._log("warning", f"Error parsing {board_config['name']} API response: {json_err}")
            except Exception as api_err:
                self._log("warning", f"Error with {board_config['name']} API: {api_err}")
        
        # If API didn't work or not available, try web scraping
        board_url = board_config['url_template'].format(company=company_id)
        self._log("info", f"Trying {board_config['name']} web URL: {board_url}")
        
        try:
            # Fetch the job board page
            board_page = self.exa.get_contents(
                urls=[board_url],
                text=True,
                livecrawl="always"
            )
            
            # Extract content for hiring info
            board_content = self._extract_content_from_response(board_page)
            if board_content and not hiring_info:
                #hiring_info_result = self._extract_hiring_info(board_content, board_url, f"job_board_{board_key}")
                hiring_info_result = board_content
                if hiring_info_result:
                    hiring_info.append(hiring_info_result)
                    self._log("info", f"Extracted hiring info from {board_config['name']} web page")
            
            # Extract links
            links = self._extract_links_from_response(board_page)
            
            if links:
                # Use LLM to identify job listing links
                job_urls = self._analyze_urls_for_job_listings(links, board_key)
                
                if job_urls:
                    # Fetch individual job listings
                    new_listings = self._fetch_job_listings(job_urls)
                    job_listings.extend(new_listings)
                    
                    if job_listings:
                        self._log("info", f"Successfully found {len(job_listings)} job listings from {board_config['name']} web")
        except Exception as e:
            self._log("warning", f"Error with {board_config['name']} web approach: {e}")
            
        return job_listings, hiring_info

    def _process_ashby_api(self, api_data: Dict[str, Any], company_id: str, api_url: str) -> Tuple[List[Dict[str, str]], List[Dict[str, Any]]]:
        """Process Ashby API response for job listings and hiring info."""
        job_listings = []
        hiring_info = []
        
        jobs = api_data.get('jobs', [])
        self._log("info", f"Successfully fetched Ashby API data: {len(jobs)} jobs found")
        
        # Extract hiring info from the API response
        if jobs:
            job_count = len(jobs)
            departments = set()
            locations = set()
            
            for job in jobs:
                if 'department' in job and job['department']:
                    departments.add(job['department'])
                if 'location' in job and job['location']:
                    locations.add(job['location'])
            
            summary = f"Found {job_count} open positions"
            if departments:
                summary += f" in departments: {', '.join(departments)}"
            if locations:
                summary += f". Locations: {', '.join(locations)}"
            
            hiring_info.append({
                "url": api_url,
                "analysis": summary,
                "source_type": "job_board_api_ashby",
                "extracted_at": datetime.now().isoformat()
            })
            self._log("info", f"Extracted hiring info from Ashby API")
        
        # Process job listings
        for job in jobs[:self.MAX_JOB_LISTINGS]:
            # Build job URL
            job_url = f"https://jobs.ashbyhq.com/{company_id}/{job.get('id')}"
            
            # Create job listing directly from API data
            job_listings.append({
                "url": job_url,
                "text": f"Title: {job.get('title', 'Unknown')}\nDepartment: {job.get('department', 'Unknown')}\nLocation: {job.get('location', 'Unknown')}\n\n{job.get('descriptionPlain', '')}",
                "summary": f"Job posting for {job.get('title', 'Unknown')} at {self.company_name}"
            })
            
        return job_listings, hiring_info

    def _process_greenhouse_api(self, api_data: Dict[str, Any], company_id: str, api_url: str) -> Tuple[List[Dict[str, str]], List[Dict[str, Any]]]:
        """Process Greenhouse API response for job listings and hiring info."""
        job_listings = []
        hiring_info = []
        
        jobs = api_data.get('jobs', [])
        self._log("info", f"Successfully fetched Greenhouse API data: {len(jobs)} jobs found")
        
        # Extract hiring info from the API response
        if jobs:
            job_count = len(jobs)
            departments = set()
            locations = set()
            
            for job in jobs:
                if 'departments' in job and job['departments']:
                    for dept in job['departments']:
                        if 'name' in dept:
                            departments.add(dept['name'])
                if 'location' in job and job['location'] and 'name' in job['location']:
                    locations.add(job['location']['name'])
            
            summary = f"Found {job_count} open positions"
            if departments:
                summary += f" in departments: {', '.join(departments)}"
            if locations:
                summary += f". Locations: {', '.join(locations)}"
            
            hiring_info.append({
                "url": api_url,
                "analysis": summary,
                "source_type": "job_board_api_greenhouse",
                "extracted_at": datetime.now().isoformat()
            })
            self._log("info", f"Extracted hiring info from Greenhouse API")
        
        # Process job listings
        for job in jobs[:self.MAX_JOB_LISTINGS]:
            # Build job URL
            job_url = job.get('absolute_url')
            if not job_url:
                job_url = f"https://boards.greenhouse.io/{company_id}/jobs/{job.get('id')}"
            
            # Extract location
            location = "Remote"
            if job.get('location', {}).get('name'):
                location = job.get('location', {}).get('name')
            
            # Extract department
            department = "N/A"
            if job.get('departments') and len(job.get('departments')) > 0:
                department = job.get('departments')[0].get('name', 'N/A')
            
            # Create job listing directly from API data
            description = job.get('content', '')
            if not description:
                description = f"Title: {job.get('title', 'Unknown Position')}\nLocation: {location}\nDepartment: {department}"
            
            job_listings.append({
                "url": job_url,
                "text": description,
                "summary": f"Job posting for {job.get('title', 'Unknown')} at {self.company_name} ({location})"
            })
            
        return job_listings, hiring_info

    def _analyze_sitemap_for_jobs(self, sitemap_urls: List[str]) -> Dict[str, List[str]]:
        """Use LLM to analyze sitemap for job-related URLs."""
        self._log("info", f"Analyzing {len(sitemap_urls)} sitemap URLs")

        messages = [
            {
                "role": "developer",
                "content": "You are a job search specialist. Your task is to analyze a company and generate search queries that will find their job listings."
            },
            {
                "role": "user",
                "content": f"""Analyze these URLs and identify:
                1. URLs that are individual job listing pages
                2. URLs that are job/careers index pages (containing lists of open positions)

                Consider variations like:
                - /jobs, /careers, /positions, /openings, /work-with-us
                - /join-our-team, /join-us, /opportunities
                - Regional variations like /jobs-uk, /careers-europe
                - Subdomains like careers.company.com, jobs.company.com

                URLs to analyze:
{chr(10).join(sitemap_urls)}

**IMPORTANT: Respond ONLY with a JSON object containing:
{{
"individual_job_listings": ["url1", "url2"],  # URLs that go directly to a job listing
"job_index_pages": ["url1", "url2"]   # URLs of pages that list multiple jobs
}}"""
            }
        ]

        analysis_result = self.track_chat_completion(messages)
        
        # Parse the result
        try:
            analysis = json.loads(analysis_result)
            self._log("info", f"Found {len(analysis.get('individual_job_listings', []))} individual listings and {len(analysis.get('job_index_pages', []))} index pages")
            return analysis
        except json.JSONDecodeError as e:
            self._log("error", f"Failed to parse LLM response: {e}")
            return {"individual_job_listings": [], "job_index_pages": []}

    def _try_all_job_boards(self) -> Tuple[List[Dict[str, str]], List[Dict[str, Any]]]:
        """Try all common job board URLs as a last resort."""
        job_listings = []
        hiring_info = []
        
        self._log("info", "Trying direct job board URLs as a last resort")
        
        # Build URLs for all job boards
        job_board_urls = []
        for board_key, config in JOB_BOARD_CONFIG.items():
            if config['url_template'] and '{company}' in config['url_template']:
                # Try with company name in lowercase and original case
                job_board_urls.append({
                    'url': config['url_template'].format(company=self.company_name.lower()),
                    'board_key': board_key
                })
                
                # Only add original case if it's different from lowercase
                if self.company_name != self.company_name.lower():
                    job_board_urls.append({
                        'url': config['url_template'].format(company=self.company_name),
                        'board_key': board_key
                    })
                
                # For iCIMS, also try with hyphens replaced with underscores (common pattern)
                if board_key == 'icims' and '-' in self.company_name:
                    job_board_urls.append({
                        'url': config['url_template'].format(company=self.company_name.lower().replace('-', '_')),
                        'board_key': board_key
                    })
        
        # Batch process URLs for efficiency
        batch_size = 4
        for i in range(0, len(job_board_urls), batch_size):
            batch = job_board_urls[i:i+batch_size]
            urls_to_try = [item['url'] for item in batch]
            board_keys = [item['board_key'] for item in batch]
            
            self._log("info", f"Batch checking {len(urls_to_try)} job board URLs")
            
            # Try to make batch requests first with simple GET
            for idx, url in enumerate(urls_to_try):
                board_key = board_keys[idx]
                try:
                    # Check if URL is accessible with a quick HEAD request
                    response = requests.head(url, timeout=5, headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    })
                    
                    if response.status_code < 400:  # Consider 2xx and 3xx as potentially valid
                        # URL is accessible, try to process it with a full GET
                        self._log("info", f"Found accessible job board: {url} ({JOB_BOARD_CONFIG[board_key]['name']})")
                        
                        # Get the full content
                        full_response = requests.get(url, timeout=10, headers={
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                        })
                        
                        if full_response.status_code == 200:
                            # Process this job board
                            new_listings, new_info = self._process_job_board(board_key, full_response.text)
                            
                            job_listings.extend(new_listings)
                            hiring_info.extend(new_info)
                            
                            # If we found job listings, we can stop here
                            if job_listings:
                                self._log("info", f"Successfully found job listings from direct job board URL: {url}")
                                return job_listings, hiring_info
                except Exception as e:
                    self._log("warning", f"Error checking {url}: {str(e)}")
                    continue
            
            # If simple requests didn't work for this batch, try with Exa
            try:
                batch_content = self.exa.get_contents(
                    urls=urls_to_try,
                    text=True,
                    livecrawl="always"
                )
                
                # Extract content from the batch request
                url_matches = re.finditer(r'<URL id=(\d+)>(.*?)</URL>', str(batch_content))
                content_matches = re.finditer(r'<Content id=(\d+)>(.*?)</Content>', str(batch_content))
                
                # Build dictionaries of URLs and content
                url_dict = {m.group(1): m.group(2) for m in url_matches}
                content_dict = {m.group(1): m.group(2) for m in content_matches}
                
                # Process each URL with content
                for idx in url_dict.keys():
                    if idx in content_dict and content_dict[idx].strip():
                        url = url_dict[idx]
                        html_content = content_dict[idx]
                        
                        # Determine which job board this is
                        board_key = None
                        for key, config in JOB_BOARD_CONFIG.items():
                            if key in url.lower():
                                board_key = key
                                break
                        
                        if board_key:
                            self._log("info", f"Processing content from job board: {url} ({JOB_BOARD_CONFIG[board_key]['name']})")
                            
                            # Process this job board
                            new_listings, new_info = self._process_job_board(board_key, html_content)
                            
                            job_listings.extend(new_listings)
                            hiring_info.extend(new_info)
                            
                            # If we found job listings, we can stop checking more pages
                            if job_listings:
                                self._log("info", f"Found job listings from job board: {url}")
                                return job_listings, hiring_info
            except Exception as e:
                self._log("warning", f"Error with batch processing: {str(e)}")
        
        return job_listings, hiring_info

    def _generate_potential_career_urls(self) -> List[str]:
        """Generate potential career URLs based on company domain."""
        # Create a prioritized list - most likely URLs first
        high_priority_urls = []
        medium_priority_urls = []
        low_priority_urls = []
        
        # High priority: careers & jobs subdomains (these are most common)
        high_priority_subdomains = ['careers', 'jobs']
        for subdomain in high_priority_subdomains:
            high_priority_urls.append(f"https://{subdomain}.{self.main_domain}")
        
        # Medium priority: other career-related subdomains
        medium_priority_subdomains = ['career', 'job', 'work', 'employment', 'recruiting']
        for subdomain in medium_priority_subdomains:
            medium_priority_urls.append(f"https://{subdomain}.{self.main_domain}")
        
        # Medium priority: common career paths on base domain
        base_url = self.company_url.rstrip('/')
        medium_priority_paths = ['/careers', '/jobs', '/join-us', '/work-with-us']
        for path in medium_priority_paths:
            medium_priority_urls.append(f"{base_url}{path}")
        
        # Lower priority: less common career paths
        low_priority_paths = ['/openings', '/opportunities', '/join-our-team', '/career', 
                            '/current-openings', '/current-opportunities', '/positions']
        for path in low_priority_paths:
            low_priority_urls.append(f"{base_url}{path}")
        
        # Low priority: base URL
        low_priority_urls.append(base_url)
        
        # Low priority: common job board URLs with company name
        for board_key, config in JOB_BOARD_CONFIG.items():
            if config['url_template'] and '{company}' in config['url_template']:
                # Try with company name in lowercase and original case
                low_priority_urls.append(config['url_template'].format(company=self.company_name.lower()))
                
                # Only add original case if it's different from lowercase
                if self.company_name != self.company_name.lower():
                    low_priority_urls.append(config['url_template'].format(company=self.company_name))
        
        # Combine all URLs in priority order
        return high_priority_urls + medium_priority_urls + low_priority_urls

    def process(self) -> GraphState:
        """Main method to fetch job listings and hiring info."""
        try:
            if not self.company_url:
                raise ValueError(f"No URL provided for branch {self.branch}")

            self._log("info", f"Starting job listing fetcher for {self.company_url}")
            self._log("info", f"Company name: {self.company_name}, Domain: {self.main_domain}")

            # Get the sitemap URLs
            sitemap_urls = self.state["branches"][self.branch].get("original_sitemap_urls", [])
            if not sitemap_urls:
                self._log("warning", "No original sitemap URLs found, falling back to filtered URLs")
                sitemap_urls = self.state["branches"][self.branch].get("sitemap_urls", [])
                self.state["branches"][self.branch]["job_listings"] = []
                return self.state

            # STAGE 1: Analyze sitemap for job-related URLs
            sitemap_analysis = self._analyze_sitemap_for_jobs(sitemap_urls)
            
            # Add career subdomains to job index pages
            career_subdomains = ['careers', 'career', 'jobs', 'job', 'work', 'employment', 'recruiting']
            subdomain_urls = [f"https://{subdomain}.{self.main_domain}" for subdomain in career_subdomains]
            
            # Ensure job_index_pages exists
            if "job_index_pages" not in sitemap_analysis:
                sitemap_analysis["job_index_pages"] = []
            
            # Add subdomain URLs with priority
            for subdomain_url in subdomain_urls:
                if subdomain_url not in sitemap_analysis["job_index_pages"]:
                    sitemap_analysis["job_index_pages"].insert(0, subdomain_url)
            
            # STAGE 2: Process individual job listings if found
            if sitemap_analysis.get("individual_job_listings"):
                urls_to_fetch = sitemap_analysis["individual_job_listings"][:self.MAX_JOB_LISTINGS]
                self._log("info", f"Fetching {len(urls_to_fetch)} individual job listings")
                
                new_listings = self._fetch_job_listings(urls_to_fetch)
                self.job_listings.extend(new_listings)
                
                ## Also extract hiring info from individual job listings
                #for listing in new_listings:
                #    if listing.get("text"):
                #        hiring_info_result = self._extract_hiring_info(listing["text"], listing["url"], "job_listing")
                #        if hiring_info_result:
                #            self.hiring_info.append(hiring_info_result)
            
            # Flag to track if we've found hiring info from a subdomain
            found_subdomain_hiring_info = False
            
            # Check career subdomains first for hiring info
            for subdomain_url in subdomain_urls:
                try:
                    self._log("info", f"Checking career subdomain for hiring info: {subdomain_url}")
                    
                    # Try to fetch the subdomain content
                    content = self._fetch_url_content(subdomain_url)
                    
                    if content and len(content.strip()) > 500:  # Ensure we have meaningful content
                        # Score the content based on relevance to careers/jobs
                        score = self._score_career_page_content(content, subdomain_url)
                        self._log("info", f"Career subdomain page score for {subdomain_url}: {score}")
                        
                        #if score > 30:  # Set a reasonable threshold for subdomain career pages
                        #    hiring_info_result = self._extract_hiring_info(content, subdomain_url, "career_subdomain")
                        #    if hiring_info_result:
                        #        self.hiring_info.append(hiring_info_result)
                        #        self._log("info", f"Extracted hiring info from subdomain career page {subdomain_url}")
                        #        found_subdomain_hiring_info = True
                        #        break
                        #    else:
                        #        # Fallback: create a basic hiring info entry with the raw content
                        #        self.hiring_info.append({
                        #            "url": subdomain_url,
                        #            "analysis": f"Career subdomain page content from {subdomain_url}. Score: {score}",
                        #            "source_type": "career_subdomain_raw",
                        #            "raw_content": content[:10000],  # Include first 10K chars of content
                        #            "extracted_at": datetime.now().isoformat()
                        #        })
                        #       self._log("info", f"Saved raw content from subdomain career page {subdomain_url}")
                        #        found_subdomain_hiring_info = True
                        #        break
                except Exception as e:
                    self._log("warning", f"Error fetching high-priority URL {subdomain_url}: {str(e)}")
            
            # If we found job listings, still check index pages but only for additional job listings if needed
            # and only check for hiring info if we haven't found it from a subdomain
            if self.job_listings:
                if len(self.job_listings) < self.MAX_JOB_LISTINGS or not found_subdomain_hiring_info:
                    self._log("info", f"Found {len(self.job_listings)} job listings from sitemap. " + 
                             (f"Looking for more job listings." if len(self.job_listings) < self.MAX_JOB_LISTINGS else "") +
                             (f" Also checking for hiring info." if not found_subdomain_hiring_info else ""))
                    
                    # Check a limited number of index pages for job listings and potentially hiring info
                    for index_page in sitemap_analysis.get("job_index_pages", [])[:5]:
                        try:
                            # Check if this is a career subdomain
                            is_subdomain = any(subdomain in index_page for subdomain in career_subdomains)
                            page_type = "subdomain index page" if is_subdomain else "regular index page"
                            
                            self._log("info", f"Processing {page_type} for {'job listings' if len(self.job_listings) < self.MAX_JOB_LISTINGS else ''}" +
                                     (f" and hiring info" if not found_subdomain_hiring_info else "") + f": {index_page}")
                            
                            index_content = self.exa.get_contents(
                                urls=[index_page],
                                text=True,
                                livecrawl="always",
                                extras={"links": 100} if len(self.job_listings) < self.MAX_JOB_LISTINGS else {}
                            )
                            
                            # Extract content
                            content_text = self._extract_content_from_response(index_content)
                            
                            # Extract hiring info only if we haven't found it from a subdomain
                            if content_text and not found_subdomain_hiring_info:
                                #hiring_info_result = self._extract_hiring_info(content_text, index_page, "career_index")
                                hiring_info_result = content_text
                                if hiring_info_result:
                                    self.hiring_info.append(hiring_info_result)
                                    self._log("info", f"Extracted hiring info from {page_type} {index_page}")
                            elif content_text and not found_subdomain_hiring_info:
                                # Fallback: create a basic hiring info entry with the raw content
                                self.hiring_info.append({
                                    "url": index_page,
                                    "analysis": f"Career page content from {index_page}.",
                                    "source_type": "career_page_raw",
                                    "raw_content": content_text[:10000],  # Include first 10K chars of content
                                    "extracted_at": datetime.now().isoformat()
                                })
                                self._log("info", f"Saved raw content from {page_type} {index_page}")
                            
                            # Extract links and find job listings if needed
                            if len(self.job_listings) < self.MAX_JOB_LISTINGS:
                                links = self._extract_links_from_response(index_content)
                                
                                if links:
                                    self._log("info", f"Found {len(links)} links in {page_type}")
                                    job_urls = self._analyze_urls_for_job_listings(links)

                                    try:
                                        if job_urls:
                                            self._log("info", f"Found {len(job_urls)} job listings in {page_type} {index_page}")
                                            new_listings = self._fetch_job_listings(job_urls)
                                            self.job_listings.extend(new_listings)
                                    
                                        # If we found enough job listings, we can stop checking more pages
                                        if len(self.job_listings) >= self.MAX_JOB_LISTINGS:
                                            self._log("info", f"Found {len(self.job_listings)} job listings, reached maximum")
                                            break
                                    except Exception as e:
                                        self._log("error", f"Failed to fetch job listings: {e}")
                        except Exception as e:
                            self._log("warning", f"Failed to process {page_type} {index_page}: {e}")
            
            # If we found job listings and hiring info by this point, we can return
            if self.job_listings and self.hiring_info:
                self._log("info", "Successfully found both job listings and hiring info")
                self.state["branches"][self.branch]["job_listings"] = self.job_listings[:self.MAX_JOB_LISTINGS]
                self.state["branches"][self.branch]["hiring_info"] = self.hiring_info
                return self.state
            
            # STAGE 3: Process job index pages if we need more data
            if len(self.job_listings) < self.MAX_JOB_LISTINGS or (not self.hiring_info and not found_subdomain_hiring_info):
                self._log("info", f"Processing job index pages for {'job listings' if len(self.job_listings) < self.MAX_JOB_LISTINGS else ''}" +
                         (f" and hiring info" if not self.hiring_info and not found_subdomain_hiring_info else ""))
                
                # Process job index pages
                if sitemap_analysis.get("job_index_pages"):
                    for index_page in sitemap_analysis["job_index_pages"]:
                        try:
                            # Check if this is a career subdomain
                            is_subdomain = any(subdomain in index_page for subdomain in career_subdomains)
                            page_type = "subdomain index page" if is_subdomain else "regular index page"
                            
                            self._log("info", f"Processing {page_type}: {index_page}")
                            
                            index_content = self.exa.get_contents(
                                urls=[index_page],
                                text=True,
                                livecrawl="always",
                                extras={"links": 100}
                            )
                            
                            # Extract content
                            content_text = self._extract_content_from_response(index_content)
                            
                            # Always extract hiring info from career pages if not already found and not found from a subdomain
                            if content_text and not self.hiring_info and not found_subdomain_hiring_info:
                                #hiring_info_result = self._extract_hiring_info(content_text, index_page, "career_index")
                                hiring_info_result = content_text
                                if hiring_info_result:
                                    self.hiring_info.append(hiring_info_result)
                                    self._log("info", f"Extracted hiring info from {page_type} {index_page}")
                            elif content_text and not self.hiring_info and not found_subdomain_hiring_info:
                                # Fallback: create a basic hiring info entry with the raw content
                                self.hiring_info.append({
                                    "url": index_page,
                                    "analysis": f"Career page content from {index_page}.",
                                    "source_type": "career_page_raw",
                                    "raw_content": content_text[:10000],  # Include first 10K chars of content
                                    "extracted_at": datetime.now().isoformat()
                                })
                                self._log("info", f"Saved raw content from {page_type} {index_page}")
                            
                            # Extract links and find job listings if needed
                            if len(self.job_listings) < self.MAX_JOB_LISTINGS:
                                links = self._extract_links_from_response(index_content)
                                
                                if links:
                                    self._log("info", f"Found {len(links)} links in {page_type}")
                                    job_urls = self._analyze_urls_for_job_listings(links)

                                    try:
                                        if job_urls:
                                            self._log("info", f"Found {len(job_urls)} job listings in {page_type} {index_page}")
                                            new_listings = self._fetch_job_listings(job_urls)
                                            self.job_listings.extend(new_listings)
                                    except Exception as e:
                                        self._log("error", f"Failed to fetch job listings: {e}")
                        except Exception as e:
                            self._log("warning", f"Failed to process {page_type} {index_page}: {e}")
            
            # STAGE 4: Check for job board integrations
            html_content = ""
            detected_career_url = ""
            career_urls = self._generate_potential_career_urls()
            
            # Try to fetch a career page
            self._log("info", f"Searching for career pages from prioritized list of {len(career_urls)} potential URLs")
            
            # Process URLs in smaller batches to avoid overloading
            batch_size = 5
            found_valid_career_page = False
            best_career_page = {"url": "", "content": "", "score": 0}
            
            # First, check high-priority URLs individually (first 5 URLs)
            for career_url in career_urls[:5]:
                try:
                    self._log("info", f"Trying high-priority career URL: {career_url}")
                    content = self._fetch_url_content(career_url)
                    
                    if content and len(content.strip()) > 500:  # Ensure we have meaningful content
                        # Score the content based on relevance to careers/jobs
                        score = self._score_career_page_content(content, career_url)
                        self._log("info", f"Career page score for {career_url}: {score}")
                        
                        if score > 0:
                            ## Always save the content to hiring_info for career pages,
                            ## even if extraction fails
                            #hiring_info_result = self._extract_hiring_info(content, career_url, "career_page")
                            #if hiring_info_result:
                            #    self.hiring_info.append(hiring_info_result)
                            #    self._log("info", f"Extracted hiring info from career page {career_url}")
                            #else:
                            #    # Fallback: create a basic hiring info entry with the raw content
                            #    self.hiring_info.append({
                            #        "url": career_url,
                            #        "analysis": f"Career page content from {career_url}. Score: {score}",
                            #        "source_type": "career_page_raw",
                            #        "raw_content": content[:10000],  # Include first 10K chars of content
                            #        "extracted_at": datetime.now().isoformat()
                            #    })
                            #    self._log("info", f"Saved raw content from career page {career_url}")
                             
                            found_valid_career_page = True
                                
                            # If this is a better page than what we've found so far, update best page
                            if score > best_career_page["score"]:
                                best_career_page = {"url": career_url, "content": content, "score": score}
                                
                                # Update HTML content for later processing
                                html_content = content
                                detected_career_url = career_url
                                
                            # Don't break - continue checking other high-priority URLs
                        else:
                            self._log("info", f"Low relevance score for {career_url}, continuing search")
                except Exception as e:
                    self._log("warning", f"Error fetching high-priority URL {career_url}: {str(e)}")
            
            # Process remaining URLs in batches
            if not found_valid_career_page or best_career_page["score"] < 50:  # If no good page found yet
                for i in range(5, len(career_urls), batch_size):
                    batch = career_urls[i:i+batch_size]
                    self._log("info", f"Processing batch of {len(batch)} URLs starting at index {i}")
                    
                    try:
                        # Batch request career URLs
                        batch_content = self.exa.get_contents(
                            urls=batch,
                            text=True,
                            livecrawl="always"
                        )
                        
                        # Process the batch results to find valid career pages
                        url_matches = re.finditer(r'<URL id=(\d+)>(.*?)</URL>', str(batch_content))
                        content_matches = re.finditer(r'<Content id=(\d+)>(.*?)</Content>', str(batch_content))
                        
                        # Build dictionaries of URLs and content
                        url_dict = {m.group(1): m.group(2) for m in url_matches}
                        content_dict = {m.group(1): m.group(2) for m in content_matches}
                        
                        # Find all URLs with valid content
                        for idx in url_dict.keys():
                            if idx in content_dict and content_dict[idx].strip():
                                career_url = url_dict[idx]
                                content = content_dict[idx]
                                
                                # Score the content
                                score = self._score_career_page_content(content, career_url)
                                self._log("info", f"Career page score for {career_url}: {score}")
                                
                                if score > 0:
                                    ## Always save the content to hiring_info for career pages,
                                    ## even if extraction fails
                                    #hiring_info_result = self._extract_hiring_info(content, career_url, "career_page")
                                    #if hiring_info_result:
                                    #    self.hiring_info.append(hiring_info_result)
                                    #    self._log("info", f"Extracted hiring info from career page {career_url}")
                                    #else:
                                    #    # Fallback: create a basic hiring info entry with the raw content
                                    #    self.hiring_info.append({
                                    #        "url": career_url,
                                    #        "analysis": f"Career page content from {career_url}. Score: {score}",
                                    #        "source_type": "career_page_raw",
                                    #        "raw_content": content[:10000],  # Include first 10K chars of content
                                    #        "extracted_at": datetime.now().isoformat()
                                    #    })
                                    #    self._log("info", f"Saved raw content from career page {career_url}")
                                     
                                    found_valid_career_page = True
                                        
                                    # If this is a better page than what we've found so far, update best page
                                    if score > best_career_page["score"]:
                                        best_career_page = {"url": career_url, "content": content, "score": score}
                                        
                                        # Update HTML content for later processing
                                        html_content = content
                                        detected_career_url = career_url
                    except Exception as e:
                        self._log("warning", f"Error with batch URL fetching at index {i}: {e}")

                        # Fallback to individual requests for this batch
                        for career_url in batch:
                            try:
                                self._log("info", f"Trying individual career URL: {career_url}")
                                content = self._fetch_url_content(career_url)
                                
                                if content and len(content.strip()) > 500:
                                    # Score the content
                                    score = self._score_career_page_content(content, career_url)
                                    self._log("info", f"Career page score for {career_url}: {score}")
                                    
                                    if score > 0:
                                        ## Always save the content to hiring_info for career pages,
                                        ## even if extraction fails
                                        #hiring_info_result = self._extract_hiring_info(content, career_url, "career_page")
                                        #if hiring_info_result:
                                        #    self.hiring_info.append(hiring_info_result)
                                        #    self._log("info", f"Extracted hiring info from career page {career_url}")
                                        #else:
                                        #    # Fallback: create a basic hiring info entry with the raw content
                                        #    self.hiring_info.append({
                                        #        "url": career_url,
                                        #        "analysis": f"Career page content from {career_url}. Score: {score}",
                                        #        "source_type": "career_page_raw",
                                        #        "raw_content": content[:10000],  # Include first 10K chars of content
                                        #        "extracted_at": datetime.now().isoformat()
                                        #    })
                                        #    self._log("info", f"Saved raw content from career page {career_url}")
                                        
                                        found_valid_career_page = True
                                            
                                        # If this is a better page than what we've found so far, update best page
                                        if score > best_career_page["score"]:
                                            best_career_page = {"url": career_url, "content": content, "score": score}
                                            
                                            # Update HTML content for later processing
                                            html_content = content
                                            detected_career_url = career_url
                            except Exception:
                                continue
                
            # Use the best career page content for further processing
            if best_career_page["score"] > 0:
                self._log("info", f"Selected best career page: {best_career_page['url']} with score {best_career_page['score']}")
                html_content = best_career_page["content"]
                detected_career_url = best_career_page["url"]
            
            # If we found a career page with content, always ensure we save it to hiring_info
            if detected_career_url and html_content and not self.hiring_info:
                self._log("info", "No hiring info extracted, but career page found. Saving raw content.")
                self.hiring_info.append({
                    "url": detected_career_url,
                    "analysis": f"Career page content from {detected_career_url}",
                    "source_type": "career_page_fallback",
                    "raw_content": html_content[:10000],  # Include first 10K chars of content
                    "extracted_at": datetime.now().isoformat()
                })
            
            # Check for job board integrations if we found a career page
            detected_job_boards = []
            if html_content and detected_career_url:
                detected_job_boards = self._detect_job_boards(html_content)
                if detected_job_boards:
                    self._log("info", f"Detected job board integrations: {detected_job_boards}")
            
            # STAGE 5: Process detected job boards
            if detected_job_boards:
                unique_boards = list(set(detected_job_boards))
                
                for board in unique_boards:
                    # Skip if we already have enough job listings and hiring info
                    if len(self.job_listings) >= self.MAX_JOB_LISTINGS and self.hiring_info:
                        break
                        
                    # Process each job board
                    new_listings, new_info = self._process_job_board(board, html_content)
                    
                    # Add results
                    self.job_listings.extend(new_listings)
                    self.hiring_info.extend(new_info)
                    
                    # If we found job listings, we can stop checking more boards
                    if new_listings:
                        self._log("info", f"Found job listings from {board}, skipping other job boards")
                        break
            
            # STAGE 6: Extract job listings from HTML content if needed
            if (not self.job_listings or len(self.job_listings) < self.MAX_JOB_LISTINGS) and html_content and detected_career_url:
                self._log("info", f"Extracting links from HTML content of {detected_career_url}")
                
                try:
                    # Extract and normalize links
                    soup = BeautifulSoup(html_content, 'html.parser')
                    all_links = [a.get('href') for a in soup.find_all('a', href=True)]
                    unique_links = self._normalize_links(all_links, detected_career_url)
                    
                    self._log("info", f"Found {len(unique_links)} unique links in HTML")
                    
                    # Analyze links for job listings
                    job_urls = self._analyze_urls_for_job_listings(unique_links, "career_page")
                    
                    if job_urls:
                        self._log("info", f"Found {len(job_urls)} job listings from HTML analysis")
                        new_listings = self._fetch_job_listings(job_urls)
                        self.job_listings.extend(new_listings)
                except Exception as e:
                    self._log("warning", f"Failed in HTML link extraction: {e}")
            
            # STAGE 7: Try direct job board APIs as a last resort if needed
            if not self.job_listings or not self.hiring_info:
                new_listings, new_info = self._try_all_job_boards()
                self.job_listings.extend(new_listings)
                self.hiring_info.extend(new_info)
            
            # Ensure we have at most MAX_JOB_LISTINGS listings
            self.job_listings = self.job_listings[:self.MAX_JOB_LISTINGS]
            
            # Store results in state
            self._log("info", f"Final job listings count: {len(self.job_listings)}/{self.MAX_JOB_LISTINGS}")
            self.state["branches"][self.branch]["job_listings"] = self.job_listings
            
            # Store hiring info if collected
            if self.hiring_info:
                self._log("info", f"Storing {len(self.hiring_info)} hiring info entries")
                self.state["branches"][self.branch]["hiring_info"] = self.hiring_info
            else:
                # If we still have no hiring info but found content from any career-related page, create a basic entry
                if html_content and detected_career_url:
                    self._log("info", "No specific hiring info found, creating generic entry with raw content")
                    self.state["branches"][self.branch]["hiring_info"] = [{
                        "url": detected_career_url,
                        "analysis": "No specific hiring information was extracted, but a career page was detected.",
                        "source_type": "fallback",
                        "raw_content": html_content[:10000],  # Include first 10K chars of content
                        "extracted_at": datetime.now().isoformat()
                    }]
                elif not html_content:
                    # Final attempt to find ANY content from career-related paths
                    self._log("info", "No career page content found, making last attempt to find any career-related content")
                    
                    # Try a few high-priority career URLs as a last resort
                    last_resort_urls = [
                        f"https://careers.{self.main_domain}",
                        f"https://jobs.{self.main_domain}",
                        f"{self.company_url.rstrip('/')}/careers",
                        f"{self.company_url.rstrip('/')}/jobs"
                    ]
                    
                    for url in last_resort_urls:
                        try:
                            content = self._fetch_url_content(url)
                            if content and len(content.strip()) > 500:
                                self._log("info", f"Found content at last resort URL: {url}")
                                self.state["branches"][self.branch]["hiring_info"] = [{
                                    "url": url,
                                    "analysis": "Limited hiring information found.",
                                    "source_type": "last_resort",
                                    "raw_content": content[:10000],
                                    "extracted_at": datetime.now().isoformat()
                                }]
                                break
                        except Exception:
                            continue
                
            return self.state

        except Exception as e:
            self._log("error", f"Unhandled exception in job listings fetcher: {str(e)}")
            self.state["branches"][self.branch]["job_listings"] = []
            # Add any collected hiring info even if we failed to get job listings
            if self.hiring_info:
                self.state["branches"][self.branch]["hiring_info"] = self.hiring_info
            return self.state


@agentstack.task
def fetch_job_listings_branch(self, state: GraphState, branch: str) -> GraphState:
    """Fetch job listings for a branch by analyzing sitemap and job pages."""
    logger.info(f"[{branch}] Starting fetch_job_listings_branch")
    
    try:
        # Set up Exa client
        exa = Exa(api_key=os.getenv("EXA_API_KEY"))
        
        # Create fetcher instance
        fetcher = JobListingFetcher(branch, state, exa)
        
        # Process job listings and update state
        updated_state = fetcher.process()
        
        return updated_state
        
    except Exception as e:
        logger.error(f"[{branch}] Error in fetch_job_listings_branch: {str(e)}")
        state["branches"][branch]["job_listings"] = []
        return state