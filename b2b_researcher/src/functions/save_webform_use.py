import os
import json
import logging
import agentstack
from typing import Dict, Any
from datetime import datetime
from src.types import GraphState
from langchain.schema import SystemMessage

@agentstack.task
def save_webform_use(self, state: GraphState) -> GraphState:
    """Save webform usage"""
    logger = logging.getLogger(__name__)
    logger.info("[[save_webform_use]]: Starting save_webform_use")
    
    # Get required inputs and validate
    inputs = state["inputs"]
    user_email = inputs.get("user_email", "")
    user_url = inputs.get("user_url", "")
    target_url = inputs.get("target_url", "")
    
    if not user_email:
        raise ValueError("User email is required")
    
    # Get reports from state for later use
    user_report = state["branches"]["user"].get("report", "")
    target_report = state["branches"]["target"].get("report", "")
    
    # First, save reports to _company_reports table
    connection_uri = os.getenv("NEON_CONNECTION_URI")
    if not connection_uri:
        raise ValueError("NEON_CONNECTION_URI environment variable not set")
        
    tool_run_sql_query = next(
        (tool for tool in agentstack.tools["neon"] if tool.__name__ == "run_sql_query"),
        None
    )
    if tool_run_sql_query is None:
        raise ValueError("Tool 'run_sql_query' not found in neon tools.")
    
    def escape(s):
        return s.replace("'", "''") if isinstance(s, str) else s
    
    # Save user report
    user_url = inputs.get("user_url", "")
    if user_report and user_url:
        # First delete any existing report
        delete_sql = f"""
            DELETE FROM _company_reports WHERE url = E'{escape(user_url)}';
        """
        tool_run_sql_query(connection_uri, delete_sql)
        
        # Then insert new report
        insert_sql = f"""
            INSERT INTO _company_reports (url, report, analysis_date)
            VALUES (
                E'{escape(user_url)}',
                E'{escape(user_report)}',
                E'{escape(self.analysis_date)}'
            );
        """
        query_result = tool_run_sql_query(connection_uri, insert_sql)
        print(f"DEBUG [[save_webform_use]]: Save user company report result: {query_result}")
    
    # Save target report
    target_url = inputs.get("target_url", "")
    if target_report and target_url:
        # First delete any existing report
        delete_sql = f"""
            DELETE FROM _company_reports WHERE url = E'{escape(target_url)}';
        """
        tool_run_sql_query(connection_uri, delete_sql)
        
        # Then insert new report
        insert_sql = f"""
            INSERT INTO _company_reports (url, report, analysis_date)
            VALUES (
                E'{escape(target_url)}',
                E'{escape(target_report)}',
                E'{escape(self.analysis_date)}'
            );
        """
        query_result = tool_run_sql_query(connection_uri, insert_sql)
        print(f"DEBUG [[save_webform_use]]: Save target company report result: {query_result}")
    
    # Then save usage info to _free_v1_webform_uses
    table_name = "_free_v1_webform_uses"
    user_email = inputs.get("user_email", "")
    insert_sql = f"""
        INSERT INTO {table_name} (
            user_email,
            user_url,
            target_url,
            final_report,
            analysis_date
        ) VALUES (
            E'{escape(user_email)}',
            E'{escape(user_url)}',
            E'{escape(target_url)}',
            NULL,
            E'{escape(self.analysis_date)}'
        );
    """
    query_result = tool_run_sql_query(connection_uri, insert_sql)
    print(f"DEBUG [[save_webform_use]]: Save webform usage result: {query_result}")
    state["messages"].append(SystemMessage(content=f"Saved free webform use record into {table_name}"))
    return state