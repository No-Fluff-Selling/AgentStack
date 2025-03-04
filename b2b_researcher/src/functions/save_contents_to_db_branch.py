import agentstack
from typing import Dict, Any, List, Optional
from src.types import GraphState
from langchain.schema import SystemMessage
import json
import os
from datetime import datetime

@agentstack.task
def save_contents_to_db_branch(self, state: GraphState, branch: str) -> GraphState:
    """Save contents to database for a branch."""
    print(f"DEBUG [{branch}] [[save_contents_to_db_branch]]: Starting save_contents_to_db_branch")
    contents = state["branches"][branch].get("page_contents")
    
    # Debug logging for contents
    print(f"DEBUG [{branch}] [[save_contents_to_db_branch]]: Contents type before storing: {type(contents)}")
    
    # Get results from contents
    results = []
    if hasattr(contents, 'results'):
        results = contents.results
    elif isinstance(contents, dict) and 'results' in contents:
        results = contents['results']
    elif isinstance(contents, list):
        results = contents
    
    # Store raw contents in state for later use
    state["branches"][branch]["raw_page_contents"] = results
    print(f"DEBUG [{branch}] [[save_contents_to_db_branch]]: Stored {len(results)} results")
    
    if results:
        print(f"DEBUG [{branch}] [[save_contents_to_db_branch]]: First result type: {type(results[0])}")
        if hasattr(results[0], '__dict__'):
            print(f"DEBUG [{branch}] [[save_contents_to_db_branch]]: First result keys: {list(results[0].__dict__.keys())}")
        print(f"DEBUG [{branch}] [[save_contents_to_db_branch]]: Sample text: {getattr(results[0], 'text', '')[:200]}")

    # Generate table name from branch URL
    url = state["inputs"].get(f"{branch}_url")
    if not url:
        print(f"ERROR [{branch}] [[save_contents_to_db_branch]]: No URL found in state inputs for key '{branch}_url'")
        print(f"DEBUG [{branch}] [[save_contents_to_db_branch]]: Available inputs: {list(state['inputs'].keys())}")
        url = state["branches"][branch].get("branch_url")  # Try fallback
        if not url:
            raise ValueError(f"No URL found for branch {branch} in state")
    
    print(f"DEBUG [{branch}] [[save_contents_to_db_branch]]: Using URL for table name: {url}")
    cleaned = url.replace("http://", "").replace("https://", "").replace("www.", "")
    if cleaned.endswith("/"):
        cleaned = cleaned[:-1]
    table_name = cleaned.replace(".", "_").replace("-", "_").replace("/", "_")
    state["branches"][branch]["table_name"] = table_name
    print(f"DEBUG [{branch}] [[save_contents_to_db_branch]]: Computed table_name: {table_name}")

    # Get SQL tools
    tool_execute_sql_ddl = next(
        (tool for tool in agentstack.tools["neon"] if tool.__name__ == "execute_sql_ddl"),
        None
    )
    tool_run_sql_query = next(
        (tool for tool in agentstack.tools["neon"] if tool.__name__ == "run_sql_query"),
        None
    )
    if tool_execute_sql_ddl is None:
        raise ValueError("Tool 'execute_sql_ddl' not found in neon tools.")
    if tool_run_sql_query is None:
        raise ValueError("Tool 'run_sql_query' not found in neon tools.")

    # Save to database
    connection_uri = os.getenv("NEON_CONNECTION_URI")
    ddl = f"""
    DROP TABLE IF EXISTS {table_name};
    CREATE TABLE {table_name} (
        id TEXT PRIMARY KEY,
        url TEXT,
        title TEXT,
        text TEXT,
        summary TEXT,
        published_date TIMESTAMP,
        image TEXT,
        favicon TEXT,
        author TEXT,
        score FLOAT,
        extras JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        analysis_date TIMESTAMP
    );
    """
    print(f"DEBUG [{branch}] [[save_contents_to_db_branch]]: DDL result: {tool_execute_sql_ddl(connection_uri, ddl)}")
    
    # Prepare inserts
    if hasattr(contents, 'results'):
        results = contents.results
        print(f"DEBUG [{branch}] [[save_contents_to_db_branch]]: Number of results to save: {len(results)}")
        insert_sqls = []
        for result in results:
            insert_sql = f"""
            INSERT INTO {table_name} (
                id, url, title, text, summary, published_date, image, favicon, author, score, extras, analysis_date
            ) VALUES (
                '{self.escape(result.id)}',
                '{self.escape(result.url)}',
                '{self.escape(result.title)}',
                '{self.escape(result.text)}',
                '{self.escape(result.summary)}',
                {f"'{result.published_date}'" if result.published_date else 'NULL'},
                {f"'{self.escape(result.image)}'" if result.image else 'NULL'},
                {f"'{self.escape(result.favicon)}'" if result.favicon else 'NULL'},
                {f"'{self.escape(result.author)}'" if result.author else 'NULL'},
                {result.score if result.score is not None else 'NULL'},
                '{json.dumps(result.extras) if result.extras else "{}"}'::jsonb,
                '{self.escape(self.analysis_date)}'
            )
            ON CONFLICT (id) DO NOTHING;
            """
            insert_sqls.append(insert_sql)
        batch_size = 100
        for i in range(0, len(insert_sqls), batch_size):
            batch_sql = "BEGIN; " + "; ".join(insert_sqls[i:i+batch_size]) + "; COMMIT;"
            query_result = tool_run_sql_query(connection_uri, batch_sql)
            print(f"DEBUG [{branch}] [[save_contents_to_db_branch]]: Batch insert result: {query_result}")
        state["messages"].append(SystemMessage(content=f"[{branch}] Saved scraped data into table '{table_name}'"))
        return state