import agentstack
from typing import Dict, Any, List
from exa_py import Exa
from exa_py.api import Result
from src.types import GraphState
from langchain.schema import SystemMessage, Document
from src.tools.exa import search_and_contents
import json
import os
from datetime import datetime, timedelta
import time

@agentstack.task
def fetch_company_news_branch(self, state: GraphState, branch: str) -> GraphState:
    print(f"DEBUG [{branch}] [[fetch_company_news_branch]]: Starting fetch_company_news_branch")
    
    try:
        # Get URL from state
        company_url = state["inputs"].get(f"{branch}_url", "")
        if not company_url:
            raise ValueError(f"No URL provided for branch {branch}")
        cleaned = company_url.replace("http://", "").replace("https://", "").replace("www.", "")
        if cleaned.endswith("/"):
            cleaned = cleaned[:-1]

        # Set table name if not already set
        if not state["branches"][branch]["table_name"]:
            table_name = cleaned.replace(".", "_").replace("-", "_").replace("/", "_")
            state["branches"][branch]["table_name"] = table_name
            print(f"DEBUG [{branch}] [[fetch_company_news_branch]]: Set table_name to: {table_name}")

        # Check if we have cached data
        table_name = state["branches"][branch]["table_name"] + "_news"
        print(f"DEBUG [{branch}] [[fetch_company_news_branch]]: Checking for cached data in table: {table_name}")
        if self.check_table_exists(table_name):
            print(f"DEBUG [{branch}] [[fetch_company_news_branch]]: Found table {table_name}")
            cached_data = self.get_cached_data(table_name, "url", company_url)
            if cached_data:
                print(f"DEBUG [{branch}] [[fetch_company_news_branch]]: Found cached data for URL: {company_url}")
                state["branches"][branch]["news_data"] = cached_data
                state["branches"][branch]["raw_news_data"] = cached_data.get("results", [])
                print(f"DEBUG [{branch}] [[fetch_company_news_branch]]: Successfully loaded cached data for {branch}")
                return state
            else:
                print(f"DEBUG [{branch}] [[fetch_company_news_branch]]: No cached data found for URL: {company_url}")
        else:
            print(f"DEBUG [{branch}] [[fetch_company_news_branch]]: Table {table_name} does not exist")
        
        # If no cached data, proceed with news fetching
        print(f"DEBUG [{branch}] [[fetch_company_news_branch]]: No cached data found for {branch}, fetching news")
        
        # Extract company name from URL for news search
        company_name = self.get_company_name_from_url(company_url)
        if not company_name:
            print(f"WARNING [[fetch_company_news_branch]]: Could not extract company name from URL for {branch}")
            return state

        # Set up exclude domains
        #exclude = [cleaned, "www." + cleaned]
        #print(f"DEBUG [{branch}] [[fetch_company_news_branch]]: Fetching news for {company_url} with exclude_domains: {exclude}")

        # Fetch news
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)  # 365 days = 12 months

        try:
            # Search for news using Exa
            news_result = search_and_contents(
                question=cleaned,
                use_autoprompt=False,
                type="keyword",
                category="news",
                num_results=25,
                text=True,
                start_published_date=start_date.strftime('%Y-%m-%d'),
                end_published_date=end_date.strftime('%Y-%m-%d'),
                summary={
                    "query": f"If the page does not contain any information about {cleaned} or information about person(s) associated with {cleaned}, or does not contain webpage text, response with only the word \"INCORRECT\"."
                }
            )
            
            # Track Exa keyword search usage
            self.track_exa_usage(branch, 'keyword', 25)
            
            time.sleep(0.2)
        except Exception as e:
            print(f"DEBUG [{branch}] [[fetch_company_news_branch]]: Error fetching company news: {e}")
            news_result = None
        
        # Parse news results    
        if news_result is None:
            parsed_news = {}
            print(f"DEBUG [{branch}] [[fetch_company_news_branch]]: No news results received")
        else:
            try:
                parsed_news = json.loads(news_result) if isinstance(news_result, str) else news_result
                print(f"DEBUG [{branch}] [[fetch_company_news_branch]]: Received news results type: {type(parsed_news)}")
            except Exception as e:
                print(f"DEBUG [{branch}] [[fetch_company_news_branch]]: Error parsing news results: {e}")
                parsed_news = {}
        
        # Process results
        news_docs = []
        if parsed_news and isinstance(parsed_news, dict):
            main_news = parsed_news.get("main", [])
            print(f"DEBUG [{branch}] [[fetch_company_news_branch]]: Number of news items in main: {len(main_news)}")
            
            results = parsed_news.get("results", [])
            if not results and "data" in parsed_news:
                results = parsed_news["data"].get("results", [])
                
            print(f"DEBUG [{branch}] [[fetch_company_news_branch]]: Processing {len(results)} news results")
            
            # Process main results
            news_data = {"main": []}
            valid_results = []  # Track valid results
            skipped_count = 0  # Track number of skipped items
            text_count = 0     # Track text content pieces
            summary_count = 0  # Track summary content pieces
            
            for r in results:
                # Skip if summary indicates incorrect data
                if r.get("summary", "").strip().upper() == "INCORRECT":
                    skipped_count += 1
                    print(f"DEBUG [{branch}] [[fetch_company_news_branch]]: Skipping item with INCORRECT summary: {r.get('url', 'no url')}")
                    continue

                # Add to news_data for state
                news_item = {
                    "title": r.get("title"),
                    "url": r.get("url"),
                    "summary": r.get("summary"),
                    "published": r.get("publishedDate"),
                    "text": r.get("text")
                }
                news_data["main"].append(news_item)
                
                # Count content pieces for Exa tracking
                if r.get("text"):
                    text_count += 1
                if r.get("summary"):
                    summary_count += 1
                
                # Create Document with metadata
                metadata = {
                    "title": r.get("title"),
                    "published_date": r.get("publishedDate"),
                    "author": r.get("author"),
                    "source_url": r.get("url"),
                    "source_type": "news"
                }
                # Filter out None values
                metadata = {k: v for k, v in metadata.items() if v is not None}
                
                doc = Document(
                    page_content=r.get("text", ""),
                    metadata=metadata
                )
                news_docs.append(doc)
                print(f"DEBUG [{branch}] [[fetch_company_news_branch]]: Added news document: {r.get('title', 'No title')} | URL: {r.get('url', 'No URL')}")
                
                # Add to valid results for database
                valid_results.append(r)
                print(f"DEBUG [{branch}] [[fetch_company_news_branch]]: Added valid news item: {news_item.get('title', 'no title')} from {news_item.get('url', 'no url')}")
            
            # Track Exa content retrieval
            if text_count > 0:
                self.track_exa_usage(branch, 'text', 0, text_count)
                print(f"DEBUG [{branch}] [[fetch_company_news_branch]]: Retrieved {text_count} pieces of text content")
            if summary_count > 0:
                self.track_exa_usage(branch, 'summary', 0, summary_count)
                print(f"DEBUG [{branch}] [[fetch_company_news_branch]]: Retrieved {summary_count} pieces of summary content")
            
            # Update state with filtered news data
            state["branches"][branch]["news_data"] = news_data
            print(f"DEBUG [{branch}] [[fetch_company_news_branch]]: Processed {len(results)} total items: {len(valid_results)} valid, {skipped_count} skipped")
            
            # Save to database if enabled
            if self.enable_db_save:
                if not state["branches"][branch]["table_name"]:
                    print(f"DEBUG [{branch}] [[fetch_company_news_branch]]: Error - table_name is empty in state")
                    return state
                    
                table_name = state["branches"][branch]["table_name"] + "_news"
                print(f"DEBUG [{branch}] [[fetch_company_news_branch]]: Creating news table: {table_name}")
                
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
                create_table_sql = f"""
                DROP TABLE IF EXISTS {table_name};
                CREATE TABLE {table_name} (
                    id SERIAL PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
                print(f"DEBUG [{branch}] [[fetch_company_news_branch]]: Created table {table_name} with result: {ddl_result}")
                
                # Insert valid news data into database
                if valid_results:
                    insert_sqls = []
                    print(f"DEBUG [{branch}] [[fetch_company_news_branch]]: Preparing to insert {len(valid_results)} items into database")
                    for r in valid_results:
                        published_date = r.get("publishedDate", "")
                        title = r.get("title", "")
                        url = r.get("url", "")
                        summary = r.get("summary", "")
                        author = r.get("author", "")
                        text = r.get("text", "")
                        
                        print(f"DEBUG [{branch}] [[fetch_company_news_branch]]: Preparing insert for article: {title} ({url})")
                        print(f"DEBUG [{branch}] [[fetch_company_news_branch]]: Article text length: {len(text) if text else 0} chars")
                        
                        insert_sql = f"""
                        INSERT INTO {table_name} (published_date, author, title, url, summary, text, analysis_date)
                        VALUES (
                            {f"'{self.escape(published_date)}'" if published_date else 'NULL'},
                            '{self.escape(author)}',
                            '{self.escape(title)}',
                            '{self.escape(url)}',
                            '{self.escape(summary)}',
                            '{self.escape(text)}',
                            '{self.escape(self.analysis_date)}'
                        );
                        """
                        insert_sqls.append(insert_sql)
                    
                    if insert_sqls:
                        print(f"DEBUG [{branch}] [[fetch_company_news_branch]]: Executing batch insert of {len(insert_sqls)} items")
                        batch_sql = "BEGIN; " + "; ".join(insert_sqls) + "; COMMIT;"
                        query_result = tool_run_sql_query(connection_uri, batch_sql)
                        print(f"DEBUG [{branch}] [[fetch_company_news_branch]]: Successfully inserted {len(insert_sqls)} valid news items into {table_name}")
                        print(f"DEBUG [{branch}] [[fetch_company_news_branch]]: Database operation result: {query_result}")
            else:
                print(f"DEBUG [{branch}] [[fetch_company_news_branch]]: Database operations are disabled, skipping save to database")
        
            state["messages"].append(SystemMessage(content=f"[{branch}] Saved news data into table '{table_name}'"))
            print(f"DEBUG [{branch}] [[fetch_company_news_branch]]: Finished fetch_company_news_branch")
            return state, news_docs

        return state

    except Exception as e:
        print(f"ERROR [[fetch_company_news_branch]]: {str(e)}")
        if "errors" not in state:
            state["errors"] = []
        state["errors"].append(f"Error fetching news for {branch}: {str(e)}")
        return state