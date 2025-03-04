import os
import json
import agentstack
from typing import Dict, Any, List
from src.types import GraphState
from datetime import datetime
from langchain.schema import SystemMessage

@agentstack.task
def save_job_listings_to_db_branch(self, state: GraphState, branch: str) -> GraphState:
    """Save job listings to database for a branch."""
    print(f"DEBUG [{branch}] [[save_job_listings_to_db_branch]]: Starting save_job_listings_to_db_branch")
    
    try:
        # Get job listings from state
        job_listings = state["branches"][branch].get("job_listings", [])
        if not job_listings:
            print(f"DEBUG [{branch}] [[save_job_listings_to_db_branch]]: No job listings to save")
            return state

        # Get table name
        if not state["branches"][branch]["table_name"]:
            print(f"DEBUG [{branch}] [[save_job_listings_to_db_branch]]: Error - table_name is empty in state")
            return state

        table_name = state["branches"][branch]["table_name"] + "_jobs"
        print(f"DEBUG [{branch}] [[save_job_listings_to_db_branch]]: Creating jobs table: {table_name}")

        # Get database tools
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

        # Save to database
        connection_uri = os.getenv("NEON_CONNECTION_URI")
        ddl = f"""
        DROP TABLE IF EXISTS {table_name};
        CREATE TABLE {table_name} (
            id TEXT PRIMARY KEY,
            url TEXT,
            title TEXT,
            text TEXT,
            author TEXT,
            published_date TIMESTAMP,
            extras JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            analysis_date TIMESTAMP
        );
        """
        print(f"DEBUG [{branch}] [[save_job_listings_to_db_branch]]: DDL result: {tool_execute_sql_ddl(connection_uri, ddl)}")
        
        # Prepare inserts
        if job_listings:
            insert_sqls = []
            print(f"DEBUG [{branch}] [[save_job_listings_to_db_branch]]: Preparing to insert {len(job_listings)} items into database")
            
            for job in job_listings:
                job_id = job.get("id", str(hash(job.get("url", ""))))
                url = job.get("url", "")
                title = job.get("title", "")
                text = job.get("text", "")
                author = job.get("author", "")
                published_date = job.get("published", "")
                extras = {
                    k: v for k, v in job.items()
                    if k not in ["id", "url", "title", "text", "author", "published"]
                }
                
                print(f"DEBUG [{branch}] [[save_job_listings_to_db_branch]]: Preparing insert for job: {title} ({url})")
                print(f"DEBUG [{branch}] [[save_job_listings_to_db_branch]]: Job text length: {len(text) if text else 0} chars")
                
                insert_sql = f"""
                INSERT INTO {table_name} (
                    id, url, title, text, author, published_date, extras, analysis_date
                ) VALUES (
                    '{self.escape(job_id)}',
                    '{self.escape(url)}',
                    '{self.escape(title)}',
                    '{self.escape(text)}',
                    '{self.escape(author)}',
                    {f"'{self.escape(published_date)}'" if published_date else 'NULL'},
                    '{json.dumps(extras)}'::jsonb,
                    '{self.escape(self.analysis_date)}'
                )
                ON CONFLICT (id) DO NOTHING;
                """
                insert_sqls.append(insert_sql)
            
            if insert_sqls:
                batch_sql = "BEGIN; " + "; ".join(insert_sqls) + "; COMMIT;"
                query_result = tool_run_sql_query(connection_uri, batch_sql)
                print(f"DEBUG [{branch}] [[save_job_listings_to_db_branch]]: Successfully inserted {len(insert_sqls)} job listings into {table_name}")
                print(f"DEBUG [{branch}] [[save_job_listings_to_db_branch]]: Database operation result: {query_result}")
        
        state["messages"].append(SystemMessage(content=f"[{branch}] Saved job listings data into table '{table_name}'"))
        print(f"DEBUG [{branch}] [[save_job_listings_to_db_branch]]: Finished save_job_listings_to_db_branch")
        return state

    except Exception as e:
        print(f"ERROR [[save_job_listings_to_db_branch]]: {str(e)}")
        state["branches"][branch]["job_listings"] = []
        return state