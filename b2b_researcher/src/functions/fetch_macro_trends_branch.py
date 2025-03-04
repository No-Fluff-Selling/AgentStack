import agentstack
from src.types import SourceDocument, GraphState
import json
import os
from datetime import datetime, timedelta
import time
import requests
from bs4 import BeautifulSoup
from exa_py import Exa
from langchain.docstore.document import Document
from typing import Dict, Any, List
from src.tools.exa import search_and_contents

@agentstack.task
def fetch_macro_trends_branch(self, state: GraphState, branch: str) -> GraphState:
    """Fetch macro trends for a branch."""
    print(f"DEBUG [{branch}] [[fetch_macro_trends_branch]]: Starting fetch_macro_trends_branch")
    
    try:
        # Get URL from state
        company_url = state["inputs"].get(f"{branch}_url", "")
        if not company_url:
            raise ValueError(f"No URL provided for branch {branch}")

        # Set table name if not already set
        if not state["branches"][branch]["table_name"]:
            table_name = company_url.replace("http://", "").replace("https://", "").replace("www.", "")
            if table_name.endswith("/"):
                table_name = table_name[:-1]
            table_name = table_name.replace(".", "_").replace("-", "_").replace("/", "_")
            state["branches"][branch]["table_name"] = table_name
            print(f"DEBUG [{branch}] [[fetch_macro_trends_branch]]: Set table_name to: {table_name}")

        # Check if we have cached data (only if database operations are enabled)
        table_name = state["branches"][branch]["table_name"] + "_trends"
        print(f"DEBUG [{branch}] [[fetch_macro_trends_branch]]: Checking for cached data in table: {table_name}")
        if self.enable_db_save:
            if self.check_table_exists(table_name):
                print(f"DEBUG [{branch}] [[fetch_macro_trends_branch]]: Found table {table_name}")
                cached_data = self.get_cached_data(table_name, "url", company_url)
                if cached_data:
                    print(f"DEBUG [{branch}] [[fetch_macro_trends_branch]]: Found cached data for URL: {company_url}")
                    state["branches"][branch]["macro_trends_data"] = cached_data
                    print(f"DEBUG [{branch}] [[fetch_macro_trends_branch]]: Successfully loaded cached data for {branch}")
                    return state
                else:
                    print(f"DEBUG [{branch}] [[fetch_macro_trends_branch]]: No cached data found for URL: {company_url}")
            else:
                print(f"DEBUG [{branch}] [[fetch_macro_trends_branch]]: Table {table_name} does not exist")
        else:
            print(f"DEBUG [{branch}] [[fetch_macro_trends_branch]]: Database operations are disabled, skipping cache check")
        
        # If no cached data, proceed with macro trends fetching
        print(f"DEBUG [{branch}] [[fetch_macro_trends_branch]]: No cached data found for {branch}, fetching macro trends")
        
        # Step 1: Identify the company's specific industry
        print(f"\nDEBUG [[fetch_macro_trends_branch]]: Identifying industry for {company_url}")
        industry_messages = [
            {
                "role": "developer",
                "content": "You are an expert at identifying companies' specific industries. "
            },
            {
                "role": "user",
                "content": f"In what specific industry/industries is {company_url}? Be precise and specific in your response. Response ONLY with a one-sentence answer that does not mention {company_url}."
            }
        ]
        
        print(f"\nDEBUG [{branch}] [[fetch_macro_trends_branch]] LLM Input for industry identification:\n{json.dumps([m['content'] for m in industry_messages], indent=2)}")
        industry_response = self.track_chat_completion(branch, industry_messages)
        print(f"\nDEBUG [{branch}] [[fetch_macro_trends_branch]] LLM Response for industry identification:\n{industry_response}")
        print(f"DEBUG [{branch}] [[fetch_macro_trends_branch]]: Identified industry: {industry_response}")
        
        # Step 2: Generate search queries based on the industry
        print("\nDEBUG [[fetch_macro_trends_branch]]: Generating search queries based on industry")
        query_messages = [
            {
                "role": "developer",
                "content": "You are a market research analyst. Respond only with a comma-separated list."
            },
            {
                "role": "user",
                "content": f"""{industry_response}
What 5 news search queries are likely to return results that summarize broad market trends, highlighting key events, policy changes, technological innovations, and any notable shifts in consumer behavior. Respond only with a comma-separated list of the exact wording of each of the search queries.
**IMPORTANT: Limit your response to ONLY a comma-separated list of the exact wording of each of the search queries.
"""
            }
        ]
        
        print(f"\nDEBUG [{branch}] [[fetch_macro_trends_branch]] LLM Input for query generation:\n{json.dumps([m['content'] for m in query_messages], indent=2)}")
        search_queries_result = self.track_chat_completion(branch, query_messages)

        print(f"\nDEBUG [{branch}] [[fetch_macro_trends_branch]] LLM Response for query generation:\n{search_queries_result}")

        # Parse the comma-separated queries and remove any quotes
        search_queries = [q.strip().strip('"\'') for q in search_queries_result.split(",")]
        print(f"\nDEBUG [{branch}] [[fetch_macro_trends_branch]]: Generated {len(search_queries)} search queries:")
        for i, query in enumerate(search_queries, 1):
            print(f"{i}. {query}")
        
        # Execute each search query
        macro_trends_data = {"main": []}
        macro_docs = []
        
        for query in search_queries:
            try:
                print(f"\nDEBUG [{branch}] [[fetch_macro_trends_branch]]: Executing search query: {query}")
                
                # Search with Exa
                results = search_and_contents(
                    question=query,
                    use_autoprompt=False,
                    type="keyword",
                    text=True,
                    num_results=5,
                    livecrawl="always"
                )
                
                # Track Exa usage
                self.track_exa_usage(branch, 'keyword', 5)
                
                time.sleep(0.2)
            except Exception as e:
                print(f"DEBUG [{branch}] [[fetch_macro_trends_branch]]: Error executing search query: {e}")
                continue
            
            # Parse results
            if isinstance(results, str):
                results = json.loads(results)
                print(f"DEBUG [{branch}] [[fetch_macro_trends_branch]]: Parsed string results into JSON")
            
            # Handle nested data structure from Exa API
            if isinstance(results, dict) and "data" in results:
                results = results["data"]
                
            if isinstance(results, dict):
                result_list = results.get("results", [])
                result_count = len(result_list)
                print(f"DEBUG [{branch}] [[fetch_macro_trends_branch]]: Found {result_count} results for query '{query}'")
                
                for r in result_list:
                    # Add to macro_trends_data for state
                    macro_trends_item = {
                        "title": r.get("title"),
                        "url": r.get("url"),
                        "summary": r.get("summary"),
                        "published": r.get("publishedDate"),
                        "text": r.get("text"),
                        "search_query": query
                    }
                    macro_trends_data["main"].append(macro_trends_item)
                    
                    # Create Document with metadata
                    metadata = {
                        "title": r.get("title"),
                        "published_date": r.get("published"),
                        "author": r.get("author"),
                        "source_url": r.get("url"),
                        "source_type": "macro_trend"
                    }
                    # Filter out None values
                    metadata = {k: v for k, v in metadata.items() if v is not None}
                    
                    text_field = r.get("text", "") or r.get("summary", "")
                    if text_field:
                        doc = Document(
                            page_content=text_field,
                            metadata=metadata
                        )
                        macro_docs.append(doc)
                        print(f"DEBUG [{branch}] [[fetch_macro_trends_branch]]: Added document from query '{query}': {r.get('title', 'No title')} | URL: {r.get('url', 'No URL')}")
                
                # Track Exa content retrieval
                #if text_count > 0:
                #    self.track_exa_usage(branch, 'text', 0, text_count)
                #    print(f"DEBUG [{branch}] [[fetch_macro_trends_branch]]: Retrieved {text_count} pieces of text content")
                #if summary_count > 0:
                #    self.track_exa_usage(branch, 'summary', 0, summary_count)
                #    print(f"DEBUG [{branch}] [[fetch_macro_trends_branch]]: Retrieved {summary_count} pieces of summary content")
            
            time.sleep(0.2)  # Rate limiting
        
        # Save to database
        # Save to database if enabled
        if self.enable_db_save:
            connection_uri = os.getenv("NEON_CONNECTION_URI")
            tool_execute_sql_ddl = next(
                (tool for tool in agentstack.tools["neon"] if tool.__name__ == "execute_sql_ddl"),
                None
            )
            tool_run_sql_query = next(
                (tool for tool in agentstack.tools["neon"] if tool.__name__ == "run_sql_query"),
                None
            )
            if tool_execute_sql_ddl is None or tool_run_sql_query is None:
                raise ValueError("Neon tools not found")

            # Create table
            if self.enable_db_save:
                table_name = "macro_trends_data"
                create_table_sql = f"""
                DROP TABLE IF EXISTS {table_name};
                CREATE TABLE {table_name} (
                    id SERIAL PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    search_query TEXT,
                    published_date TIMESTAMP,
                    author TEXT,
                    title TEXT,
                    url TEXT,
                    summary TEXT,
                    text TEXT,
                    analysis_date TIMESTAMP
                );
                """
                ddl_result = tool_execute_sql_ddl(connection_uri, create_table_sql)
                print(f"DEBUG [{branch}] [[fetch_macro_trends_branch]]: Created table {table_name} with result: {ddl_result}")
                
                # Insert data
                if macro_trends_data["main"]:
                    insert_sqls = []
                    print(f"DEBUG [{branch}] [[fetch_macro_trends_branch]]: Preparing to insert {len(macro_trends_data['main'])} items into database")
                    
                    for r in macro_trends_data["main"]:
                        insert_sql = f"""
                        INSERT INTO {table_name} (search_query, published_date, title, url, summary, text, analysis_date)
                        VALUES (
                            '{self.escape(r.get("search_query", ""))}',
                        {f"'{self.escape(r.get('published', ''))}'"
 if r.get('published') else 'NULL'},
                        '{self.escape(r.get("title", ""))}',
                        '{self.escape(r.get("url", ""))}',
                        '{self.escape(r.get("summary", ""))}',
                        '{self.escape(r.get("text", ""))}',
                        '{self.escape(self.analysis_date)}'
                    );
                    """
                    insert_sqls.append(insert_sql)
                
                if insert_sqls:
                    batch_sql = "BEGIN; " + "; ".join(insert_sqls) + "; COMMIT;"
                    query_result = tool_run_sql_query(connection_uri, batch_sql)
                    print(f"DEBUG [{branch}] [[fetch_macro_trends_branch]]: Inserted {len(insert_sqls)} items into {table_name}")
            else:
                print(f"DEBUG [{branch}] [[fetch_macro_trends_branch]]: Database operations are disabled, skipping table creation and data insertion")
        
        # Update state
        state["branches"][branch]["macro_trends_data"] = macro_trends_data
        state["branches"][branch]["macro_trends_docs"] = macro_docs
        
        print(f"DEBUG [{branch}] [[fetch_macro_trends_branch]]: Finished processing {len(macro_docs)} documents from {len(search_queries)} queries")
        return state
        
    except Exception as e:
        print(f"ERROR [[fetch_macro_trends_branch]]: {str(e)}")
        state["branches"][branch]["macro_trends_data"] = {}
        state["branches"][branch]["macro_trends_docs"] = []
        return state