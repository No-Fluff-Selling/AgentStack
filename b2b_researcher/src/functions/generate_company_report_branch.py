import agentstack
from typing import Dict, Any
from src.types import GraphState
from langchain.schema import SystemMessage

@agentstack.task
def generate_company_report_branch(self, state: GraphState, branch: str) -> GraphState:
    """Generate a company report for a branch using branch-specific report generators."""
    print(f"DEBUG [{branch}] [[generate_company_report_branch]]: Starting generate_company_report_branch")
    try:
        if branch == "user":
            report = self.generate_user_company_report(state)
        else:  # branch == "target"
            report = self.generate_target_company_report(state)
        state["branches"][branch]["report"] = report
        state["messages"].append(SystemMessage(content=f"[{branch}] Generated company report (first 200 chars): {report[:200]}"))
        print(f"DEBUG [{branch}] [[generate_company_report_branch]]: Generated report length: {len(report)} characters")
        print(f"DEBUG [{branch}] [[generate_company_report_branch]]: Finished generate_company_report_branch")
        return state
    except Exception as e:
        print(f"ERROR in report generation: {str(e)}")
        import traceback
        traceback.print_exc()
        raise