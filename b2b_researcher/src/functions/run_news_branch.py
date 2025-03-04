import agentstack
from typing import Dict, Any
from src.types import GraphState
from langgraph.graph import StateGraph

@agentstack.task
def run_news_branch(self, state: GraphState, branch: str) -> GraphState:
    """Run the news steps for a branch."""
    try:
        # Create a StateGraph for this branch's news operations
        branch_graph = StateGraph(
            state_schema=dict
        )
        
        # Define node functions
        def start_node(inputs: dict):
            return inputs
            
        def fetch_company_news_node(inputs: dict):
            return {"state": self.fetch_company_news_branch(inputs["state"], branch=branch)}
            
        def end_node(inputs: dict):
            return inputs
        
        # Add nodes for each step
        branch_graph.add_node("start", start_node)
        branch_graph.add_node("fetch_company_news", fetch_company_news_node)
        branch_graph.add_node("end", end_node)
        
        # Add edges to connect the steps
        branch_graph.add_edge("start", "fetch_company_news")
        branch_graph.add_edge("fetch_company_news", "end")
        
        # Set entry and finish points
        branch_graph.set_entry_point("start")
        branch_graph.set_finish_point("end")
        
        # Run the graph
        app = branch_graph.compile()
        result = app.invoke({"state": state})
        return result["state"]
        
    except Exception as e:
        print(f"ERROR [[run_news_branch]]: Error in news branch '{branch}': {str(e)}")
        if "errors" not in state:
            state["errors"] = []
        state["errors"].append(f"Error in news branch '{branch}': {str(e)}")
        return state