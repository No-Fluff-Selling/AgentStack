<<<<<<< HEAD
import os
import json
import logging
import time
import copy

# Configure logging to use INFO level
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Union, Optional, Tuple
from typing_extensions import TypedDict, Annotated
from dataclasses import dataclass
from langchain.docstore.document import Document
from src.types import SourceDocument, BranchState, GraphState
import re
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import operator

# Use updated community imports to support RAG (FAISS, embeddings)
from langchain_community.vectorstores import FAISS
from langchain.prompts import ChatPromptTemplate
from langchain.text_splitter import CharacterTextSplitter
from langchain.schema import SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.channels import Topic, LastValue
from langchain_community.chat_models import ChatOpenAI
from langchain_openai import OpenAIEmbeddings

# Imports specifically for get_db_connection (required for fetching data from Neon database)
import agentstack
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

# Import report templates
from src.prompts.user_report_templates import (
    USER_REPORT_TEMPLATE,
    USER_VERIFICATION_PROMPT,
    USER_REQUIRED_SECTIONS,
    USER_FOCUS_AREAS,
    USER_FALLBACK_QUERIES
)
from src.prompts.target_report_templates import (
    TARGET_REPORT_TEMPLATE,
    TARGET_VERIFICATION_PROMPT,
    TARGET_REQUIRED_SECTIONS,
    TARGET_FOCUS_AREAS,
    TARGET_FALLBACK_QUERIES,
    COMPANY_OVERVIEW_TEMPLATE,
    OPEN_POSITIONS_TEMPLATE,
    NEWS_TEMPLATE,
    MACRO_TRENDS_TEMPLATE
)

# Import functions from functions directory
from src.functions.apply_verification import apply_verification
from src.functions.fetch_company_news_branch import fetch_company_news_branch
from src.functions.fetch_job_listings_branch import fetch_job_listings_branch
from src.functions.fetch_macro_trends_branch import fetch_macro_trends_branch
from src.functions.fetch_page_contents_branch import fetch_page_contents_branch
from src.functions.generate_adaptive_queries import generate_adaptive_queries
from src.functions.fix_citation_sequence import fix_citation_sequence
from src.functions.format_job_listings import format_job_listings
from src.functions.generate_company_report_branch import generate_company_report_branch
from src.functions.generate_fallback_queries import generate_fallback_queries
from src.functions.generate_target_company_report import generate_target_company_report
from src.functions.fetch_sitemap_urls_branch import fetch_sitemap_urls_branch
from src.functions.generate_user_company_report import generate_user_company_report
from src.functions.get_cached_data import get_cached_data
from src.functions.get_news_docs import get_news_docs
from src.functions.get_table_name_for_branch import get_table_name_for_branch
from src.functions.get_webpage_docs import get_webpage_docs
from src.functions.make_json_serializable import make_json_serializable
from src.functions.merge_branch_states import merge_branch_states
from src.functions.save_company_report_to_db import save_company_report_to_db
from src.functions.save_contents_to_db_branch import save_contents_to_db_branch
from src.functions.save_job_listings_to_db_branch import save_job_listings_to_db_branch
from src.functions.save_webform_use import save_webform_use
from src.functions.should_continue_retrieval import should_continue_retrieval
from src.functions.validate_target_report_content import validate_target_report_content
from src.functions.validate_user_report_content import validate_user_report_content
from src.functions.verify_coverage import verify_coverage
from src.functions.wrap_node import wrap_node
from src.functions.initialize_state import initialize_state
from src.functions.finalize_state import finalize_state
from src.functions.execute_rag_process import execute_rag_process
from src.functions.generate_target_company_report import generate_section_with_deepseek

###############################################################################
# Define the main graph class.
###############################################################################
class B2bresearcherGraph:
    def __init__(self, enable_db_save: bool = True):
        """Initialize the B2bresearcherGraph with current date and token tracking.
        
        Args:
            enable_db_save (bool): Whether to save data to the database. Defaults to True.
        """
        from datetime import datetime
        self.analysis_date = datetime.now().strftime("%Y-%m-%d")
        self.start_time = time.time()
        self._state = None
        self._error = None
        self.enable_db_save = enable_db_save
        
        if not enable_db_save:
            logging.info("Database saving is disabled. No data will be saved to the database.")
        
        # Initialize token and cost tracking
        self.token_usage = {
            'user': {
                'gpt4': {'input_tokens': 0, 'output_tokens': 0},
                'o1-preview': {'input_tokens': 0, 'output_tokens': 0},
                'o1-mini': {'input_tokens': 0, 'output_tokens': 0},
                'o3-mini': {'input_tokens': 0, 'output_tokens': 0},
                'ada': {'input_tokens': 0, 'output_tokens': 0}
            },
            'target': {
                'gpt4': {'input_tokens': 0, 'output_tokens': 0},
                'o1-preview': {'input_tokens': 0, 'output_tokens': 0},
                'o1-mini': {'input_tokens': 0, 'output_tokens': 0},
                'o3-mini': {'input_tokens': 0, 'output_tokens': 0},
                'ada': {'input_tokens': 0, 'output_tokens': 0}
            }
        }
        
        # Initialize Exa API usage tracking
        self.exa_usage = {
            'user': {
                'neural_search_small': 0,  # 1-25 results
                'neural_search_large': 0,  # 26-100 results
                'keyword_search': 0,       # 1-100 results
                'content_text': 0,         # Content retrieval without summary/highlight
                'content_summary': 0,      # Content retrieval with summary
                'content_highlight': 0     # Content retrieval with highlight
            },
            'target': {
                'neural_search_small': 0,
                'neural_search_large': 0,
                'keyword_search': 0,
                'content_text': 0,
                'content_summary': 0,
                'content_highlight': 0
            }
        }
        
        # Initialize RAG configuration
        self.rag_config = {
            'max_iterations': 6,
            'queries_per_batch': 8,
            'docs_per_query': 15,
            'min_confidence_score': 0.72,
            'context_window': 4000,  # Reduced from 6500
            'chunk_overlap': 250,
            'max_cumulative_context': 50000,  # 50k input + 15k output buffer
            'response_token_buffer': 15000,
            'compression_ratio': 0.7
        }
        
        # API costs per unit
        self.api_costs = {
            'gpt4': {'input': 10.00, 'output': 30.00},    # $10/1M input, $30/1M output
            'o1-preview': {'input': 15.00, 'output': 60.00},      # $15/1M input, $60/1M output
            'o1-mini': {'input': 1.10, 'output': 4.40},    # $1.10/1M input, $4.40/1M output
            'o3-mini': {'input': 1.10, 'output': 4.40},    # $1.10/1M input, $4.40/1M output
            'ada': {'input': 0.10, 'output': 0.10},       # $0.10/1M tokens for embeddings
            'exa': {
                'neural_search_small': 5.00,  # $5.00/1k searches (1-25 results)
                'neural_search_large': 25.00, # $25.00/1k searches (26-100 results)
                'keyword_search': 2.50,       # $2.50/1k searches
                'content_text': 1.00,         # $1.00/1k pieces of content (text)
                'content_summary': 1.50,      # $1.50/1k pieces of content (summary)
                'content_highlight': 2.00     # $2.00/1k pieces of content (highlight)
            }
        }
        
    def escape(self, s):
        """Escape single quotes in strings for SQL queries."""
        return s.replace("'", "''") if isinstance(s, str) else s

    def track_tokens(self, branch: str, model: str, input_tokens: int, output_tokens: int):
        """Track token usage for a specific branch and model"""
        if branch not in self.token_usage:
            return
        
        if model == 'text-embedding-ada-002':
            model_key = 'ada'
        elif model == 'gpt-4':
            model_key = 'gpt4'
        elif model == 'o1-preview':
            model_key = 'o1-preview'
        elif model == 'o3-mini':
            model_key = 'o3-mini'
        else:
            model_key = 'o1-mini'
            
        self.token_usage[branch][model_key]['input_tokens'] += input_tokens
        self.token_usage[branch][model_key]['output_tokens'] += output_tokens

    def track_exa_usage(self, branch: str, search_type: str, num_results: int, content_count: int = 0):
        """Track Exa API usage for searches and content retrieval"""
        if branch not in self.exa_usage:
            return
            
        if search_type == 'neural':
            if num_results <= 25:
                self.exa_usage[branch]['neural_search_small'] += 1
            else:
                self.exa_usage[branch]['neural_search_large'] += 1
        elif search_type == 'keyword':
            self.exa_usage[branch]['keyword_search'] += 1
            
        if content_count > 0:
            if search_type == 'text':
                self.exa_usage[branch]['content_text'] += content_count
            elif search_type == 'summary':
                self.exa_usage[branch]['content_summary'] += content_count
            elif search_type == 'highlight':
                self.exa_usage[branch]['content_highlight'] += content_count

    def track_chat_completion(self, branch: str, messages: list) -> str:
        """Track tokens for chat completion and return response"""
        # Import OpenAI
        import os
        import tiktoken
        from openai import OpenAI
        
        # Use OpenAI client directly
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Format messages for OpenAI API - keep original roles (including "developer")
        api_messages = []
        for message in messages:
            api_messages.append({"role": message["role"], "content": message["content"]})
        
        # If api_messages is empty, use the last message content
        if not api_messages:
            api_messages = [{"role": "user", "content": messages[-1]["content"]}]
        
        # For token counting
        encoder = tiktoken.get_encoding("cl100k_base")
        input_text = " ".join([m["content"] for m in api_messages])
        input_tokens = len(encoder.encode(input_text))
        
        # Call API without temperature parameter
        response = client.chat.completions.create(
            model="o3-mini",
            messages=api_messages,
        )
        
        content = response.choices[0].message.content
        output_tokens = len(encoder.encode(content))
        
        # Track tokens
        self.track_tokens(branch, "o3-mini", input_tokens, output_tokens)
        
        return content

    def track_embedding(self, branch: str, text: str):
        """Track tokens for embedding operations"""
        # Estimate tokens
        estimated_tokens = len(text.split()) * 1.3  # Rough estimate
        self.track_tokens(branch, 'text-embedding-ada-002', int(estimated_tokens), 0)

    def calculate_costs(self):
        """Calculate API costs for each branch and model"""
        costs = {'user': 0.0, 'target': 0.0, 'total': 0.0}
        
        for branch in ['user', 'target']:
            # Calculate LLM costs
            for model in ['gpt4', 'o1-preview', 'o1-mini', 'o3-mini', 'ada']:
                usage = self.token_usage[branch][model]
                model_costs = self.api_costs[model]
                
                input_cost = (usage['input_tokens'] / 1_000_000) * model_costs['input']
                output_cost = (usage['output_tokens'] / 1_000_000) * model_costs['output']
                costs[branch] += input_cost + output_cost
            
            # Calculate Exa API costs
            exa_usage = self.exa_usage[branch]
            exa_costs = self.api_costs['exa']
            
            neural_small_cost = (exa_usage['neural_search_small'] / 1_000) * exa_costs['neural_search_small']
            neural_large_cost = (exa_usage['neural_search_large'] / 1_000) * exa_costs['neural_search_large']
            keyword_cost = (exa_usage['keyword_search'] / 1_000) * exa_costs['keyword_search']
            content_text_cost = (exa_usage['content_text'] / 1_000) * exa_costs['content_text']
            content_summary_cost = (exa_usage['content_summary'] / 1_000) * exa_costs['content_summary']
            content_highlight_cost = (exa_usage['content_highlight'] / 1_000) * exa_costs['content_highlight']
            
            costs[branch] += neural_small_cost + neural_large_cost + keyword_cost + content_text_cost + content_summary_cost + content_highlight_cost
        
        costs['total'] = costs['user'] + costs['target']
        return costs

    def print_usage_report(self):
        """Print detailed usage report including runtime and costs"""
        runtime = time.time() - self.start_time
        minutes = runtime / 60
        
        print("\n" + "=" * 80)
        print("USAGE REPORT")
        print("=" * 80 + "\n")
        
        print(f"Total Runtime: {runtime:.2f} seconds ({minutes:.2f} minutes)\n")
        
        print("Token Usage:")
        for branch in ['user', 'target']:
            print(f"\n{branch.upper()} BRANCH:")
            for model in ['gpt4', 'o1-preview', 'o1-mini', 'o3-mini', 'ada']:
                usage = self.token_usage[branch][model]
                total_tokens = usage['input_tokens'] + usage['output_tokens']
                cost = ((usage['input_tokens'] / 1_000_000) * self.api_costs[model]['input'] +
                       (usage['output_tokens'] / 1_000_000) * self.api_costs[model]['output'])
                print(f"  {model}:")
                print(f"    Input Tokens:  {usage['input_tokens']:,}")
                print(f"    Output Tokens: {usage['output_tokens']:,}")
                print(f"    Total Tokens:  {total_tokens:,}")
                print(f"    Cost:          ${cost:.4f}")
        
        print("\nExa API Usage:")
        for branch in ['user', 'target']:
            print(f"\n{branch.upper()} BRANCH:")
            usage = self.exa_usage[branch]
            exa_costs = self.api_costs['exa']
            
            # Calculate search costs
            ns_small_cost = (usage['neural_search_small'] / 1_000) * exa_costs['neural_search_small']
            ns_large_cost = (usage['neural_search_large'] / 1_000) * exa_costs['neural_search_large']
            kw_cost = (usage['keyword_search'] / 1_000) * exa_costs['keyword_search']
            
            # Calculate content costs
            text_cost = (usage['content_text'] / 1_000) * exa_costs['content_text']
            summary_cost = (usage['content_summary'] / 1_000) * exa_costs['content_summary']
            highlight_cost = (usage['content_highlight'] / 1_000) * exa_costs['content_highlight']
            
            # Print search usage and costs
            print("  Search Usage:")
            print(f"    Neural Search (1-25):  {usage['neural_search_small']:,} (${ns_small_cost:.4f})")
            print(f"    Neural Search (26+):   {usage['neural_search_large']:,} (${ns_large_cost:.4f})")
            print(f"    Keyword Search:        {usage['keyword_search']:,} (${kw_cost:.4f})")
            
            # Print content usage and costs
            print("  Content Usage:")
            print(f"    Text Content:          {usage['content_text']:,} (${text_cost:.4f})")
            print(f"    Summary Content:       {usage['content_summary']:,} (${summary_cost:.4f})")
            print(f"    Highlight Content:     {usage['content_highlight']:,} (${highlight_cost:.4f})")
            
            # Print subtotals
            total_search_cost = ns_small_cost + ns_large_cost + kw_cost
            total_content_cost = text_cost + summary_cost + highlight_cost
            print("  Subtotals:")
            print(f"    Search Cost:           ${total_search_cost:.4f}")
            print(f"    Content Cost:          ${total_content_cost:.4f}")
            print(f"    Total Branch Cost:     ${(total_search_cost + total_content_cost):.4f}")
        
        costs = self.calculate_costs()
        print("\nGRAND TOTAL:                 ${costs['total']:.4f}")
        
        print("\n" + "=" * 80)
    
    # ----- Tasks for each branch -----
    def merge_branch_states(self, base_state: GraphState, scraping_state: GraphState, news_state: GraphState, branch: str) -> GraphState:
        """Helper method to merge states from different branch operations."""
        return merge_branch_states(self, base_state, scraping_state, news_state, branch)

    fetch_sitemap_urls_branch = fetch_sitemap_urls_branch

    def fetch_company_news_branch(self, state: GraphState, branch: str) -> GraphState:
        """Fetch company news for a branch."""
        return fetch_company_news_branch(self, state, branch)

    def fetch_job_listings_branch(self, state: GraphState, branch: str) -> GraphState:
        """Fetch job listings for a branch."""
        return fetch_job_listings_branch(self, state, branch)

    def save_job_listings_to_db_branch(self, state: GraphState, branch: str) -> GraphState:
        """Save job listings to database for a branch."""
        if not self.enable_db_save:
            logging.info(f"Skipping job listings save for branch {branch} (database saving disabled)")
            return state
        return save_job_listings_to_db_branch(self, state, branch)

    def save_webform_use(self, state: GraphState) -> GraphState:
        """Save webform use data."""
        if not self.enable_db_save:
            logging.info("Skipping webform use save (database saving disabled)")
            return state
        return save_webform_use(self, state)

    def make_json_serializable(self, obj: Any, depth: int = 0) -> Any:
        """Make an object JSON serializable."""
        return make_json_serializable(self, obj, depth)

    def fetch_page_contents_branch(self, state: GraphState, branch: str) -> GraphState:
        """Fetch page contents for a branch."""
        return fetch_page_contents_branch(self, state, branch)

    def generate_section_with_deepseek(self, prompt: str, section_name: str):
        """Generate a section using DeepSeek."""
        return generate_section_with_deepseek(self, prompt, section_name)
    
    def generate_user_company_report(self, state: GraphState) -> GraphState:
        """Generate user company report."""
        return generate_user_company_report(self, state)

    def generate_target_company_report(self, state: GraphState) -> GraphState:
        """Generate target company report."""
        return generate_target_company_report(self, state)

    def generate_company_overview(self, state: GraphState) -> GraphState:
        """Generate company overview section."""
        print("DEBUG [[generate_company_overview]]: Generating company overview section")
        
        # Get template variables from state
        template_vars = self._get_template_variables(state)
        
        # Ensure required keys are present
        required_keys = ["company_name", "user_company_name", "webpage_context", "citations", "user_report"]
        for key in required_keys:
            if key not in template_vars:
                print(f"WARNING [[generate_company_overview]]: {key} not found in template_vars, adding default value")
                template_vars[key] = "" if key != "company_name" else "Unknown Company"
                
        # Generate the section content
        prompt = self._get_company_overview_prompt(template_vars)
        content = self.generate_section_with_deepseek(prompt, "Company Overview")
        
        # Strip markdown code block markers if present
        content = self._strip_markdown_code_blocks(content)
        
        # Initialize sections dictionary if not present
        state["sections"] = state.get("sections", {})
        
        # Store the generated section
        state["sections"]["overview"] = content
        print("DEBUG [[generate_company_overview]]: Company overview section generated")
        return state

    def generate_open_positions(self, state: GraphState) -> GraphState:
        """Generate open positions section."""
        print("DEBUG [[generate_open_positions]]: Generating open positions section")
        
        # Get template variables from state
        template_vars = self._get_template_variables(state)
        
        # Ensure required keys are present
        required_keys = ["company_name", "user_company_name", "job_context", "hiring_info_context", "citations"]
        for key in required_keys:
            if key not in template_vars:
                print(f"WARNING [[generate_open_positions]]: {key} not found in template_vars, adding default value")
                template_vars[key] = "" if key != "company_name" else "Unknown Company"
                
        # Generate the section content
        prompt = self._get_open_positions_prompt(template_vars)
        content = self.generate_section_with_deepseek(prompt, "Open Positions")
        
        # Strip markdown code block markers if present
        content = self._strip_markdown_code_blocks(content)
        
        # Initialize sections dictionary if not present
        state["sections"] = state.get("sections", {})
        
        # Store the generated section
        state["sections"]["positions"] = content
        print("DEBUG [[generate_open_positions]]: Open positions section generated")
        return state

    def generate_news_section(self, state: GraphState) -> GraphState:
        """Generate news section."""
        print("DEBUG [[generate_news_section]]: Generating news section")
        
        # Get template variables from state
        template_vars = self._get_template_variables(state)
        
        # Ensure required keys are present
        required_keys = ["company_name", "user_company_name", "news_context", "webpage_context", "citations", "user_report"]
        for key in required_keys:
            if key not in template_vars:
                print(f"WARNING [[generate_news_section]]: {key} not found in template_vars, adding default value")
                template_vars[key] = "" if key != "company_name" else "Unknown Company"
                
        # Generate the section content
        prompt = self._get_news_prompt(template_vars)
        content = self.generate_section_with_deepseek(prompt, "News Section")
        
        # Strip markdown code block markers if present
        content = self._strip_markdown_code_blocks(content)
        
        # Initialize sections dictionary if not present
        state["sections"] = state.get("sections", {})
        
        # Store the generated section
        state["sections"]["news"] = content
        print("DEBUG [[generate_news_section]]: News section generated")
        return state

    def generate_macro_trends(self, state: GraphState) -> GraphState:
        """Generate macro trends section."""
        print("DEBUG [[generate_macro_trends]]: Generating macro trends section")
        
        # Get template variables from state
        template_vars = self._get_template_variables(state)
        
        # Ensure required keys are present
        required_keys = ["company_name", "user_company_name", "macro_context", "citations"]
        for key in required_keys:
            if key not in template_vars:
                print(f"WARNING [[generate_macro_trends]]: {key} not found in template_vars, adding default value")
                template_vars[key] = "" if key != "company_name" else "Unknown Company"
                
        # Generate the section content
        prompt = self._get_macro_trends_prompt(template_vars)
        content = self.generate_section_with_deepseek(prompt, "Macro Trends")
        
        # Strip markdown code block markers if present
        content = self._strip_markdown_code_blocks(content)
        
        # Initialize sections dictionary if not present
        state["sections"] = state.get("sections", {})
        
        # Store the generated section
        state["sections"]["trends"] = content
        print("DEBUG [[generate_macro_trends]]: Macro trends section generated")
        return state

    def combine_sections(self, state: GraphState) -> GraphState:
        """Combine all sections into final report."""
        print("DEBUG [[combine_sections]]: Combining all sections into final report")
        
        # Check if all required sections exist
        required_sections = ["overview", "positions", "news", "trends"]
        for section in required_sections:
            if "sections" not in state or section not in state.get("sections", {}):
                print(f"WARNING [[combine_sections]]: {section} section not found in state, report may be incomplete")
        
        # Get sections from state
        company_overview = state.get("sections", {}).get("overview", "## Company Overview\nNo content available.")
        open_positions = state.get("sections", {}).get("positions", "## Open Positions\nNo content available.")
        news_section = state.get("sections", {}).get("news", "## Recent News\nNo content available.")
        macro_trends = state.get("sections", {}).get("trends", "## Macro Trends\nNo content available.")
        
        # Strip markdown code block markers from each section if present
        company_overview = self._strip_markdown_code_blocks(company_overview)
        open_positions = self._strip_markdown_code_blocks(open_positions)
        news_section = self._strip_markdown_code_blocks(news_section)
        macro_trends = self._strip_markdown_code_blocks(macro_trends)
        
        # Get template variables from target_report_data
        if "target_report_data" not in state:
            print("ERROR [[combine_sections]]: target_report_data not found in state")
            # Create a minimal set of template variables to avoid KeyError
            template_vars = {
                "company_name": "Unknown Company",
                "user_company_name": "Your Company",
                "news_context": "",
                "webpage_context": "",
                "job_context": "",
                "macro_context": "",
                "citations": "No citations available.",
                "user_report": "",
                "hiring_info_context": ""
            }
        else:
            template_vars = state["target_report_data"]
        
        # Get company names from template_vars
        company_name = template_vars.get("company_name", "Unknown Company")
        user_company_name = template_vars.get("user_company_name", "Your Company")
        
        # Create a custom report template that uses the generated sections
        CUSTOM_REPORT_TEMPLATE = """---

# {company_name} Intelligence Report

{company_overview}

{open_positions}

{news_section}

{macro_trends}

---

#### Note: This analysis is based on publicly available information from {company_name}'s online presence, news coverage, and market research.
#### Want more in-depth information about this industry and companies operating in it? Contact us at <a href="mailto:sales@nofluffselling.com" target="_blank">sales@nofluffselling.com</a>.</b>

## Citations
{citations}
"""
        
        # Format the final report using the custom template with generated sections
        report = CUSTOM_REPORT_TEMPLATE.format(
            company_name=company_name,
            user_company_name=user_company_name,
            company_overview=company_overview,
            open_positions=open_positions,
            news_section=news_section,
            macro_trends=macro_trends,
            citations=template_vars.get("citations", "No citations available.")
        )
        
        # Strip markdown code block markers from the final report
        report = self._strip_markdown_code_blocks(report)
        
        # Fix citation sequence in the combined report
        if "target_report_data" in state and "source_metadata" in state["target_report_data"]:
            print("DEBUG [[combine_sections]]: Running fix_citation_sequence on combined report")
            source_metadata = state["target_report_data"]["source_metadata"]
            report = fix_citation_sequence(report, source_metadata)
        else:
            print("WARNING [[combine_sections]]: Could not run fix_citation_sequence, source_metadata not found")
        
        # Ensure the branches and target branch exist in state
        if "branches" not in state:
            state["branches"] = {}
        if "target" not in state["branches"]:
            state["branches"]["target"] = {}
        
        # Store the final report in the correct location in state
        state["branches"]["target"]["report"] = report
        print("DEBUG [[combine_sections]]: Final report generated and stored in state['branches']['target']['report']")
        
        return state

    def get_cached_data(self, table_name: str, branch: str, state: GraphState) -> Dict[str, Any]:
        """Get cached data from a table."""
        return get_cached_data(self, table_name, branch, state)

    def get_webpage_docs(self, state: GraphState, branch: str) -> List[Document]:
        """Get webpage documents for a branch."""
        # Check if documents are already available in state
        if branch == "target" and "target_webpage_docs" in state:
            print(f"DEBUG [{branch}] [[get_webpage_docs]]: Using pre-created webpage documents from state")
            return state["target_webpage_docs"]
        elif branch == "user" and "user_webpage_docs" in state:
            print(f"DEBUG [{branch}] [[get_webpage_docs]]: Using pre-created webpage documents from state")
            return state["user_webpage_docs"]
        
        return get_webpage_docs(self, state, branch)

    def get_news_docs(self, state: GraphState, branch: str) -> List[Document]:
        """Get news documents for a branch."""
        # Check if documents are already available in state
        if branch == "target" and "target_news_docs" in state:
            print(f"DEBUG [{branch}] [[get_news_docs]]: Using pre-created news documents from state")
            return state["target_news_docs"]
        elif branch == "user" and "user_news_docs" in state:
            print(f"DEBUG [{branch}] [[get_news_docs]]: Using pre-created news documents from state")
            return state["user_news_docs"]
            
        return get_news_docs(self, state, branch)

    execute_rag_process = execute_rag_process

    def _wrap_node(self, node_func):
        """Wrap a node function with error handling and state tracking."""
        # Extract node name from function name (remove _node suffix if present)
        node_name = node_func.__name__
        if node_name.endswith("_node"):
            node_name = node_name[:-5]  # Remove "_node" suffix
        
        def wrapped(state: GraphState) -> GraphState:
            try:
                # Add node start message to state
                if "messages" not in state:
                    state["messages"] = []
                
                # Add a structured message that includes the node name and status
                state["messages"].append({
                    "name": node_name,
                    "status": "running",
                    "timestamp": time.time()
                })
                
                print(f"DEBUG [[wrap_node]]: Starting node {node_name}")
                self._state = state  # Track current state
                
                # Execute the node function
                result = node_func(state)
                
                # Add completion message to result state
                if "messages" not in result:
                    result["messages"] = []
                
                # Add a structured message that includes the node name and status
                result["messages"].append({
                    "name": node_name,
                    "status": "done", 
                    "timestamp": time.time()
                })
                
                print(f"DEBUG [[wrap_node]]: Completed node {node_name}")
                self._state = result  # Update state after successful execution
                return result
            except Exception as e:
                error_message = f"Node {node_name} execution failed: {str(e)}"
                print(f"ERROR [[wrap_node]]: {error_message}")
                
                # Update state with error information
                if "errors" not in state:
                    state["errors"] = []
                state["errors"].append(error_message)
                
                # Add error message
                if "messages" not in state:
                    state["messages"] = []
                
                # Add a structured message that includes the node name, status, and error
                state["messages"].append({
                    "name": node_name, 
                    "status": "error", 
                    "error": str(e),
                    "timestamp": time.time()
                })
                
                self._error = str(e)
                return state
        return wrapped

    def _initialize_state(self, state: GraphState) -> GraphState:
        """Initialize the graph state."""
        return initialize_state(self, state)
        
    def _finalize_state(self, state: GraphState) -> GraphState:
        """Finalize the graph state and prepare the final report."""
        return finalize_state(self, state)

    def get_company_name_from_url(self, url: str) -> str:
        """Extract company name from URL."""
        # Remove protocol and www
        cleaned = url.replace("http://", "").replace("https://", "").replace("www.", "")
        # Remove trailing slash
        if cleaned.endswith("/"):
            cleaned = cleaned[:-1]

        # Get domain part
        company = cleaned.split("/")[0]
        # Remove .com, .org, etc
        company = company.split(".")[0]
        # Convert dashes to spaces and capitalize
        company = company.replace("-", " ").title()
        return company

    def run(self, inputs: Dict[str, str]):
        """Run the graph using LangGraph."""
        try:
            # Initialize state
            print("DEBUG [[run]]: Starting graph execution")
            print("DEBUG [[run]]: Initializing state")
            initial_state = {
                "inputs": inputs,
                "messages": [],
                "branches": {
                    "user": {"report": ""},
                    "target": {"report": ""}
                },
                "vector_stores": {},
                "errors": []
            }
            state = self._initialize_state(initial_state)
            print("DEBUG [[run]]: Initialized graph state")
            yield state
            
            # Compile the graph
            print("DEBUG [[run]]: Compiling graph")
            graph = self.compile()
            print("DEBUG [[run]]: Graph compiled")
            
            # Run the graph using LangGraph
            print("DEBUG [[run]]: Executing graph")
            # The StateGraph itself doesn't have invoke() - we need to compile it to get a runnable
            runnable = graph.compile()
            print("DEBUG [[run]]: Graph compiled into runnable")
            result = runnable.invoke({"state": state})
            
            # Get the final state from the result
            final_state = result["state"]
            
            # Print debug info about what was processed
            if "branches" in final_state:
                if final_state["branches"]["user"].get("report"):
                    print("DEBUG [[run]]: User report generated")
                if final_state["branches"]["target"].get("report"):
                    print("DEBUG [[run]]: Target report generated")
            
            # Yield the final state
            yield final_state
            
            # Save webform usage
            try:
                print("DEBUG [[run]]: Starting save_webform_use")
                state = self.save_webform_use(final_state)
                print("DEBUG [[run]]: Finished save_webform_use")
            except Exception as e:
                print(f"ERROR [[run]]: Error saving webform use: {str(e)}")
            
            # Print usage report
            self.print_usage_report()
            
            # Finalize and store final state
            state = self._finalize_state(state)
            self._state = state
            
            # Yield the finalized state
            yield state
            
        except Exception as e:
            print(f"ERROR [[run]]: Error in graph execution: {str(e)}")
            self._error = str(e)
            raise

    @property
    def total_steps(self) -> int:
        """Return the total number of steps in the graph."""
        # 10 steps: initialize, user (4 steps), target (4 steps), finalize
        return 10

    @contextmanager
    def get_db_connection(self):
        """Get a database connection."""
        if not self.enable_db_save:
            raise RuntimeError("Database operations are disabled")
            
        connection_uri = os.getenv("NEON_CONNECTION_URI")
        if not connection_uri:
            raise ValueError("NEON_CONNECTION_URI environment variable not set")
        
        conn = psycopg2.connect(connection_uri)
        try:
            yield conn
        finally:
            conn.close()
    
    def check_table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the Neon database."""
        if not self.enable_db_save:
            print(f"DEBUG [[check_table_exists]]: Database operations disabled, skipping table check for '{table_name}'")
            return False
            
        print(f"DEBUG [[check_table_exists]]: Checking if table '{table_name}' exists")
        
        if not table_name:
            print("ERROR [[check_table_exists]]: Empty table name provided")
            return False
            
        try:
            with self.get_db_connection() as conn:
                with conn.cursor() as cur:
                    query = """
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public'
                            AND table_name = %s
                        );
                    """
                    print(f"DEBUG [[check_table_exists]]: Executing query with table_name: {table_name}")
                    cur.execute(query, (table_name,))
                    exists = cur.fetchone()[0]
                    print(f"DEBUG [[check_table_exists]]: Table '{table_name}' {'exists' if exists else 'does not exist'}")
                    return exists
        except Exception as e:
            print(f"ERROR [[check_table_exists]]: Error checking table existence: {str(e)}")
            return False

    def compile(self) -> Any:
        """Compile the graph into a StateGraph object that can be executed."""
        try:
            from typing_extensions import Annotated
            import operator
            
            # Define a custom merge function for dictionaries
            def merge_dicts(dict1, dict2):
                """Merge two dictionaries by creating a new one with values from both."""
                result = dict1.copy() if isinstance(dict1, dict) else {}
                
                # Handle different types of dict2
                if isinstance(dict2, dict):
                    result.update(dict2)
                elif isinstance(dict2, list) and all(isinstance(item, dict) for item in dict2):
                    # If dict2 is a list of dictionaries, merge them all
                    for item in dict2:
                        result.update(item)
                elif isinstance(dict2, tuple) and len(dict2) == 2:
                    # Handle tuple format (key, value)
                    key, value = dict2
                    # Check if key is hashable
                    try:
                        hash(key)
                        result[key] = value
                    except TypeError:
                        # If key is a dict, don't try to use it as a key, but merge its contents
                        if isinstance(key, dict):
                            # Silently merge the key dictionary into the result
                            result.update(key)
                            
                            # If value is also a dict, merge it too
                            if isinstance(value, dict):
                                result.update(value)
                            else:
                                # If value is not a dict, store it with a special key
                                result["_value_from_dict_key"] = value
                        else:
                            # For other unhashable types, convert to string
                            try:
                                string_key = str(key)
                                result[string_key] = value
                            except Exception as e:
                                print(f"Error converting key to string: {e}")
                else:
                    print(f"Warning: Unexpected format in merge_dicts: {type(dict2)}, {dict2}")
                
                return result
            
            # Define a state schema that supports parallel operations
            class GraphStateSchema(TypedDict):
                state: Annotated[dict, merge_dicts]
            
            # Create the graph with our custom state schema
            graph = StateGraph(
                state_schema=GraphStateSchema
            )
            
            # Define node functions
            def start_node(inputs: dict):
                return inputs
                
            def user_sitemap_node(inputs: dict):
                return {"state": self.fetch_sitemap_urls_branch(inputs["state"], "user")}
                
            def user_scraping_node(inputs: dict):
                return {"state": self.fetch_page_contents_branch(inputs["state"], "user")}
                
            def user_report_node(inputs: dict):
                return {"state": self.generate_user_company_report(inputs["state"])}
                
            def target_sitemap_node(inputs: dict):
                return {"state": self.fetch_sitemap_urls_branch(inputs["state"], "target")}
                
            def target_scraping_node(inputs: dict):
                return {"state": self.fetch_page_contents_branch(inputs["state"], "target")}
                
            def target_news_node(inputs: dict):
                return {"state": self.fetch_company_news_branch(inputs["state"], "target")}
                
            def target_job_listings_node(inputs: dict):
                state = inputs["state"]
                # First run the job listings branch
                state = self.fetch_job_listings_branch(state, "target")
                # Then save the listings
                state = self.save_job_listings_to_db_branch(state, "target")
                return {"state": state}
            
            def target_macro_trends_node(inputs: dict):
                state = inputs["state"]
                print("DEBUG [[target_macro_trends_node]]: Fetching macro trends data")
                state = self.fetch_macro_trends_branch(state, "target")
                print(f"DEBUG [[target_macro_trends_node]]: Macro trends data fetched, keys in branch: {list(state['branches']['target'].keys())}")
                if "macro_trends_data" in state["branches"]["target"]:
                    print(f"DEBUG [[target_macro_trends_node]]: Found {len(state['branches']['target']['macro_trends_data'].get('main', []))} macro trends items")
                return {"state": state}
                
            def target_report_node(inputs: dict):
                state = inputs["state"].copy()
                print("DEBUG [[target_report_node]]: Generating target company report data")
                state = self.generate_target_company_report(state)
                print("DEBUG [[target_report_node]]: Target company report data generated")
                return {"state": state}
                
            # New sequential report generation nodes
            def overview_node(inputs: dict):
                state = inputs["state"].copy()  # Make a copy to avoid modifying the original
                # Ensure we're using target_report_data
                if "target_report_data" not in state:
                    print("ERROR [[overview_node]]: target_report_data not found in state")
                    raise ValueError("target_report_data not found in state")
                
                print("DEBUG [[overview_node]]: Generating company overview section")
                state = self.generate_company_overview(state)
                
                return {"state": state}
                
            def positions_node(inputs: dict):
                state = inputs["state"].copy()  # Make a copy to avoid modifying the original
                # Ensure we're using target_report_data
                if "target_report_data" not in state:
                    print("ERROR [[positions_node]]: target_report_data not found in state")
                    raise ValueError("target_report_data not found in state")
                
                # Ensure job_context is present in target_report_data
                if "job_context" not in state["target_report_data"]:
                    print("WARNING [[positions_node]]: job_context not found in target_report_data, adding default value")
                    state["target_report_data"]["job_context"] = "No job listings found."
                
                print("DEBUG [[positions_node]]: Generating open positions section")
                state = self.generate_open_positions(state)
                
                return {"state": state}
                
            def news_section_node(inputs: dict):
                state = inputs["state"].copy()  # Make a copy to avoid modifying the original
                # Ensure we're using target_report_data
                if "target_report_data" not in state:
                    print("ERROR [[news_section_node]]: target_report_data not found in state")
                    raise ValueError("target_report_data not found in state")
                
                print("DEBUG [[news_section_node]]: Generating news section")
                state = self.generate_news_section(state)
                
                return {"state": state}
                
            def macro_trends_node(inputs: dict):
                state = inputs["state"].copy()  # Make a copy to avoid modifying the original
                # Ensure we're using target_report_data
                if "target_report_data" not in state:
                    print("ERROR [[macro_trends_node]]: target_report_data not found in state")
                    raise ValueError("target_report_data not found in state")
                
                print("DEBUG [[macro_trends_node]]: Generating macro trends section")
                state = self.generate_macro_trends(state)
                
                return {"state": state}
                
            def combine_sections_node(inputs: dict):
                state = inputs["state"].copy()  # Make a copy to avoid modifying the original
                # Ensure we're using target_report_data
                if "target_report_data" not in state:
                    print("ERROR [[combine_sections_node]]: target_report_data not found in state")
                    raise ValueError("target_report_data not found in state")
                
                print("DEBUG [[combine_sections_node]]: Combining all sections into final report")
                state = self.combine_sections(state)
                
                return {"state": state}
                
            def end_node(inputs: dict):
                # The state is already finalized in the run method
                return inputs
            
            # Add nodes for each step
            graph.add_node("start", start_node)
            graph.add_node("user_sitemap", user_sitemap_node)
            graph.add_node("user_scraping", user_scraping_node)
            graph.add_node("user_report", user_report_node)
            
            graph.add_node("target_sitemap", target_sitemap_node)
            graph.add_node("target_scraping", target_scraping_node)
            graph.add_node("target_news", target_news_node)
            graph.add_node("target_job_listings", target_job_listings_node)
            graph.add_node("target_macro_trends", target_macro_trends_node)
            
            graph.add_node("target_report", target_report_node)
            graph.add_node("overview", overview_node)
            graph.add_node("positions", positions_node)
            graph.add_node("news_section", news_section_node)
            graph.add_node("macro_trends", macro_trends_node)
            graph.add_node("combine_sections", combine_sections_node)
            
            graph.add_node("end", end_node)
            
            # Add edges to connect the steps
            # Start with user branch
            graph.add_edge("start", "user_sitemap")
            graph.add_edge("user_sitemap", "user_scraping")
            graph.add_edge("user_scraping", "user_report")

            # After user report is complete, start target branch sequentially
            graph.add_edge("user_report", "target_sitemap")
            graph.add_edge("target_sitemap", "target_scraping")
            graph.add_edge("target_scraping", "target_news")
            graph.add_edge("target_news", "target_job_listings")
            graph.add_edge("target_job_listings", "target_macro_trends")
            graph.add_edge("target_macro_trends", "target_report")

            # Sequential section generation
            graph.add_edge("target_report", "overview")
            graph.add_edge("overview", "positions")
            graph.add_edge("positions", "news_section")
            graph.add_edge("news_section", "macro_trends")
            graph.add_edge("macro_trends", "combine_sections")
            graph.add_edge("combine_sections", "end")
            
            # Set entry and finish points
            graph.set_entry_point("start")
            graph.set_finish_point("end")
            
            return graph
            
        except Exception as e:
            print(f"ERROR [[compile]]: Error compiling graph: {str(e)}")
            raise

    @property
    def current_state(self) -> Optional[dict]:
        """Return the current state of the graph."""
        return self._state

    @property
    def error(self) -> Optional[str]:
        """Return any error that occurred during graph execution."""
        return self._error

    def load_config(self):
        """Load RAG config from environment variable or default to empty dict"""
        config_str = os.getenv("RAG_CONFIG", "{}")
        try:
            return json.loads(config_str)
        except json.JSONDecodeError:
            print("Error parsing RAG config. Using default config.")
            return {}

    def save_contents_to_db_branch(self, state: GraphState, branch: str) -> GraphState:
        """Save contents to database for a branch."""
        if not self.enable_db_save:
            logging.info(f"Skipping database save for branch {branch} (database saving disabled)")
            return state
        return save_contents_to_db_branch(self, state, branch)

    def track_chat_completion(self, branch: str, messages: List[Dict[str, str]]) -> str:
        """Track chat completion usage."""
        return self.chat_completion(messages)

    def generate_adaptive_queries(self, collected_docs: List[Document], n_queries: int, branch: str, company_name: str) -> List[str]:
        """Generate follow-up queries based on collected documents and branch type."""
        return generate_adaptive_queries(self, collected_docs, n_queries, branch, company_name)

    def generate_fallback_queries(self, n_queries: int, branch: str) -> List[str]:
        """Generate fallback queries in case of error."""
        return generate_fallback_queries(self, n_queries, branch)

    def format_job_listings(self, job_listings):
        """Format job listings into a readable summary."""
        return format_job_listings(self, job_listings)

    def chat_completion(self, messages: List[Dict[str, str]]) -> str:
        """Get chat completion from OpenAI."""
        import os
        from openai import OpenAI
        
        # Use OpenAI client directly
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Format messages for OpenAI API - keep original roles (including "developer")
        api_messages = []
        for message in messages:
            api_messages.append({"role": message["role"], "content": message["content"]})
        
        # If api_messages is empty, use the last message content
        if not api_messages:
            api_messages = [{"role": "user", "content": messages[-1]["content"]}]
        
        # For token counting
        import tiktoken
        encoder = tiktoken.get_encoding("cl100k_base")
        input_text = " ".join([m["content"] for m in api_messages])
        input_tokens = len(encoder.encode(input_text))
        
        # Call API without temperature parameter
        response = client.chat.completions.create(
            model="o3-mini",
            messages=api_messages,
        )
        
        content = response.choices[0].message.content
        output_tokens = len(encoder.encode(content))
        
        # Track tokens
        self.track_tokens("target", "o3-mini", input_tokens, output_tokens)
        
        return content

    def validate_user_report_content(self, report_text: str, company_name: str) -> Tuple[bool, str]:
        """Validate if the user company report contains all critical elements and proper citations."""
        return validate_user_report_content(self, report_text, company_name)

    def save_company_report_to_db(self, state: GraphState, branch: str) -> GraphState:
        """Save company report to database for a branch."""
        if not self.enable_db_save:
            logging.info(f"Skipping company report save for branch {branch} (database saving disabled)")
            return state
        return save_company_report_to_db(self, state, branch)

    def fix_citation_sequence(self, report: str, source_metadata: Dict[str, Any]) -> str:
        """Attempt to fix citation sequence in the generated report."""
        return fix_citation_sequence(report, source_metadata)

    def fetch_macro_trends_branch(self, state: GraphState, branch: str) -> GraphState:
        """Fetch macro trends for a branch."""
        return fetch_macro_trends_branch(self, state, branch)
    
    def validate_target_report_content(self, report_text: str, company_name: str, user_company_name: str = "") -> Tuple[bool, str]:
        """Validate if the target company report contains all critical elements and proper citations."""
        try:
            # Check for required sections
            required_sections = [
                f"1. Open Positions",
                f"2. Current Events (Last 6 Months)",
                f"3. Macro Trends",
                f"4. {company_name} Info"
            ]
            
            missing_sections = []
            for section in required_sections:
                if section not in report_text:
                    missing_sections.append(section)
            
            if missing_sections:
                return False, f"Missing required sections: {', '.join(missing_sections)}"
            
            # Check for citations
            citation_pattern = r'\[(\d+)\]'
            citations = re.findall(citation_pattern, report_text)
            
            if not citations:
                return False, "No citations found in report"
            
            # Check citation sequence
            citation_numbers = [int(c) for c in citations]
            max_citation = max(citation_numbers)
            expected_sequence = list(range(1, max_citation + 1))
            
            if set(citation_numbers) != set(expected_sequence):
                return False, f"Invalid citation sequence. Expected: {expected_sequence}, Found: {sorted(list(set(citation_numbers)))}"
            
            # Check for company name mentions
            if company_name not in report_text:
                return False, f"Company name '{company_name}' not found in report"
            
            # Check for specific content indicators
            content_indicators = {
                "job listings": ["hiring", "position", "job", "role", "opening"],
                "current events": ["recent", "news", "announced", "launched", "update"],
                "macro trends": ["trend", "industry", "market", "growth", "forecast"],
                "company info": ["product", "service", "offer", "solution", "platform"]
            }
            
            missing_content = []
            for section, indicators in content_indicators.items():
                found = False
                for indicator in indicators:
                    if indicator.lower() in report_text.lower():
                        found = True
                        break
                if not found:
                    missing_content.append(section)
            
            if missing_content:
                return False, f"Missing content indicators for sections: {', '.join(missing_content)}"
            
            return True, "Report validation successful"
            
        except Exception as e:
            print(f"ERROR [[validate_target_report_content]]: {str(e)}")
            return False, str(e)

    def _get_template_variables(self, state: GraphState) -> dict:
        """Get template variables for report generation."""
        # Determine the current context by checking what we're generating
        # If we're in one of the target company report sections, we should use target_report_data
        is_target_context = True  # Default to target context for sequential execution
        
        # Check if target_report_data is already available in state
        if "target_report_data" in state:
            print("DEBUG [[_get_template_variables]]: Using pre-prepared target_report_data")
            template_vars = state["target_report_data"]
            print(f"DEBUG [[_get_template_variables]]: template_vars keys: {list(template_vars.keys())}")
            return template_vars
        
        print("DEBUG [[_get_template_variables]]: Generating template variables from scratch")
        # Get company information
        company_url = state["inputs"].get("target_url", "")
        company_name = self.get_company_name_from_url(company_url)
        user_company_name = self.get_company_name_from_url(state["inputs"].get("user_url", ""))
        
        # Get documents - check if they're already in state to avoid recreating them
        if "target_webpage_docs" in state:
            print("DEBUG [[_get_template_variables]]: Using pre-created webpage documents from state")
            webpage_docs = state["target_webpage_docs"]
        else:
            webpage_docs = self.get_webpage_docs(state, "target")
            # Store for future use
            state["target_webpage_docs"] = webpage_docs
        
        if "target_news_docs" in state:
            print("DEBUG [[_get_template_variables]]: Using pre-created news documents from state")
            news_docs = state["target_news_docs"]
        else:
            news_docs = self.get_news_docs(state, "target")
            # Store for future use
            state["target_news_docs"] = news_docs
        
        # Get job listings documents
        job_listings_docs = []
        if "target_job_listings_docs" in state:
            print("DEBUG [[_get_template_variables]]: Using pre-created job listings documents from state")
            job_listings_docs = state["target_job_listings_docs"]
        elif "job_listings" in state["branches"]["target"]:
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
            # Store for future use
            state["target_job_listings_docs"] = job_listings_docs
        
        # Get macro trends documents
        macro_trends_docs = []
        if "target_macro_trends_docs" in state:
            print("DEBUG [[_get_template_variables]]: Using pre-created macro trends documents from state")
            macro_trends_docs = state["target_macro_trends_docs"]
        elif "macro_trends_data" in state["branches"]["target"]:
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
            # Store for future use
            state["target_macro_trends_docs"] = macro_trends_docs
        
        # Get user company report from state
        user_report = state["branches"]["user"].get("report", "No user company report available")
        
        # Generate citations
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
        
        citations = "\n".join(sorted_citations)
        
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
        
        # Return template variables
        template_vars = {
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
        
        # Store the template variables in state
        print("DEBUG [[_get_template_variables]]: Storing template variables in state['target_report_data']")
        state["target_report_data"] = template_vars

        return template_vars

    def _get_company_overview_prompt(self, template_vars: dict) -> str:
        """Get company overview prompt template."""
        return COMPANY_OVERVIEW_TEMPLATE.format(**template_vars)
    
    def _get_open_positions_prompt(self, template_vars: dict) -> str:
        """Get open positions prompt template."""
        return OPEN_POSITIONS_TEMPLATE.format(**template_vars)
    
    def _get_news_prompt(self, template_vars: dict) -> str:
        """Get news prompt template."""
        return NEWS_TEMPLATE.format(**template_vars)
    
    def _get_macro_trends_prompt(self, template_vars: dict) -> str:
        """Get macro trends prompt template."""
        return MACRO_TRENDS_TEMPLATE.format(**template_vars)

    def _strip_markdown_code_blocks(self, content: str) -> str:
        """Strip markdown code block markers from the given content."""
        # Remove markdown code block markers
        content = content.replace("```markdown", "").replace("```", "")
        return content

    def run_with_progress_tracking(self, inputs: Dict[str, Any], on_step=None):
        """
        Run the graph with progress tracking.
        
        Args:
            inputs: Input values for the graph
            on_step: Callback function for tracking progress, with signature (state, step_id, step_description)
            
        Returns:
            The final state after graph execution
        """
        # Initialize state
        state = None
        
        try:
            # Run the graph and track progress
            for state_update in self.run(inputs):
                state = state_update
                
                # Process messages if they exist
                if state and "messages" in state:
                    for message in state.get("messages", []):
                        # Only process node execution messages
                        if isinstance(message, dict) and "name" in message:
                            step_id = message.get("name")
                            status = message.get("status", "running")
                            
                            # Extract description based on status
                            if status == "running":
                                description = f"Started {step_id}"
                            elif status == "done":
                                description = f"Completed {step_id}"
                            elif status == "error":
                                description = f"Error in {step_id}: {message.get('error', 'Unknown error')}"
                            else:
                                description = f"{step_id}: {status}"
                            
                            # Call the progress callback if provided
                            if on_step:
                                on_step(state, step_id, description)
            
            return state
        except Exception as e:
            print(f"ERROR [[run_with_progress_tracking]]: {str(e)}")
            if state is not None:
                # Add error message to state
                if "messages" not in state:
                    state["messages"] = []
                state["messages"].append({"name": "graph_execution", "status": "error", "error": str(e)})
                
                # Call the error callback if provided
                if on_step:
                    on_step(state, "graph_execution", f"Error: {str(e)}")
            
            # Re-raise the exception for proper handling
            raise
=======
from typing import Annotated
from typing_extensions import TypedDict

from langchain.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_openai import ChatOpenAI


import agentstack


class State(TypedDict):
    inputs: dict[str, str]
    messages: Annotated[list, add_messages]


class B2bresearcherGraph:

    @agentstack.task
    def scrape_single_page(self, state: State):
        task_config = agentstack.get_task('scrape_single_page')
        messages = ChatPromptTemplate.from_messages([
            ("user", task_config.prompt), 
        ])
        messages = messages.format_messages(**state['inputs'])
        return {'messages': messages + state['messages']}

    @agentstack.agent
    def web_scraper(self, state: State):
        agent_config = agentstack.get_agent('web_scraper')
        messages = ChatPromptTemplate.from_messages([
            ("user", agent_config.prompt), 
        ])
        messages = messages.format_messages(**state['inputs'])
        agent = ChatOpenAI(model=agent_config.model)
        # Filter firecrawl tools to only use web_scrape
        firecrawl_tools = [tool for tool in agentstack.tools['firecrawl'] if tool.__name__ == 'web_scrape']
        agent = agent.bind_tools([*firecrawl_tools, *agentstack.tools['exa'], *agentstack.tools['perplexity']])
        response = agent.invoke(
            messages + state['messages'],
        )
        return {'messages': [response, ]}

    def run(self, inputs: list[str]):
        # Filter firecrawl tools to only use web_scrape
        firecrawl_tools = [tool for tool in agentstack.tools['firecrawl'] if tool.__name__ == 'web_scrape']
        tools = ToolNode([*firecrawl_tools, *agentstack.tools['exa'], *agentstack.tools['perplexity']])
        self.graph = StateGraph(State)
        self.graph.add_edge(START, "scrape_single_page")
        self.graph.add_edge("scrape_single_page", "web_scraper")
        self.graph.add_edge("web_scraper", END)
        
        self.graph.add_conditional_edges("web_scraper", tools_condition)
        self.graph.add_edge("tools", "web_scraper")
        self.graph.add_node("scrape_single_page", self.scrape_single_page)
        self.graph.add_node("web_scraper", self.web_scraper)
        self.graph.add_node("tools", tools)
        

        app = self.graph.compile()
        result_generator = app.stream({
            'inputs': inputs,
            'messages': [],
        })

        for message in result_generator:
            for k, item in message.items():
                for m in item['messages']:
                    agentstack.log.notify(f"\n\n{k}:")
                    agentstack.log.info(m.content)

>>>>>>> 3252885aeb05c6aeec4a6f96d50df7e2f0974956
