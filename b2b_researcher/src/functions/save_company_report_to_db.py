import os
import json
import agentstack
from typing import Dict, Any
from datetime import datetime
from src.types import GraphState, CustomJSONEncoder
from langchain.schema import SystemMessage

@agentstack.task
def save_company_report_to_db(self, state: GraphState, branch: str) -> GraphState:
    """Save company report to database for a branch."""
    print(f"DEBUG [{branch}] [[save_company_report_to_db]]: Starting save_company_report_to_db")
    report = state["branches"][branch].get("report", "")
    company_url = state["inputs"].get(f"{branch}_url", "")
    connection_uri = os.getenv("NEON_CONNECTION_URI")
    tool_run_sql_query = next(
        (tool for tool in agentstack.tools["neon"] if tool.__name__ == "run_sql_query"),
        None
    )
    if tool_run_sql_query is None:
        raise ValueError("Tool 'run_sql_query' not found in neon tools.")

    # Convert report to JSON string if it's a dict or contains SystemMessage objects
    if isinstance(report, (dict, list)) or any(isinstance(x, SystemMessage) for x in state.get("messages", [])):
        report = json.dumps(report, cls=CustomJSONEncoder)

    # First delete any existing report for this URL
    delete_sql = f"""
        DELETE FROM _company_reports WHERE url = E'{self.escape(company_url)}';
    """
    tool_run_sql_query(connection_uri, delete_sql)
    
    # Then insert the new report, using E'' syntax for escaping special characters
    insert_sql = f"""
        INSERT INTO _company_reports (url, report, analysis_date)
        VALUES (
            E'{self.escape(company_url)}',
            E'{self.escape(report)}',
            E'{self.escape(self.analysis_date)}'
        );
    """
    query_result = tool_run_sql_query(connection_uri, insert_sql)
    print(f"DEBUG [{branch}] [[save_company_report_to_db]]: Save company report result: {query_result}")
    state["messages"].append(SystemMessage(content=f"[{branch}] Saved report to _company_reports"))
    return state