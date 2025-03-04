import os
import time
import logging
import re
from typing import Dict, Any, List
import agentstack
from src.types import GraphState

def strip_markdown_code_blocks(content: str) -> str:
    """Strip markdown code block markers from the given content."""
    # Remove markdown code block markers
    if not content:
        return content
    
    # Remove triple backtick markdown blocks
    content = re.sub(r'```(?:markdown)?\s*\n', '', content)
    content = re.sub(r'\n```', '', content)
    
    return content

@agentstack.task
def finalize_state(self, state: GraphState) -> GraphState:
    """Finalize the graph state and prepare the final report."""
    logger = logging.getLogger(__name__)
    logger.info("[[finalize]]: Starting finalization")
    
    try:
        # Validate state structure
        if "branches" not in state:
            raise ValueError("Missing 'branches' in state")
        if "user" not in state["branches"]:
            raise ValueError("Missing 'user' branch in state")
        if "target" not in state["branches"]:
            raise ValueError("Missing 'target' branch in state")
            
        # Get reports from both branches and strip markdown code block markers if present
        user_report = state["branches"]["user"].get("report", "")
        target_report = state["branches"]["target"].get("report", "")
        
        # Strip markdown code block markers from user report
        user_report = strip_markdown_code_blocks(user_report)
            
        # Strip markdown code block markers from target report
        target_report = strip_markdown_code_blocks(target_report)
        
        # Ensure citations are properly fixed in both reports
        # Note: The fix_citation_sequence method should already have been called 
        # on both reports during their respective generation processes
        
        # Validate reports
        if not user_report:
            logger.warning("User report is empty")
        if not target_report:
            logger.warning("Target report is empty")
        
        # Check for any errors during execution
        errors = state.get("errors", [])
        error_section = ""
        if errors:
            error_section = "\n\n## Execution Errors\n" + "<br>\n".join([f"- {error}" for error in errors]) + "<br>"
        
        # Combine the reports into a single markdown string with user report first
        final_markdown = f"""
{user_report}
<br>
<br>
{target_report}
<br>
{error_section}

---
*Report generated on {self.analysis_date}*
"""
        
        # Create the final report structure
        final_report = {
            "report": final_markdown,
            "metadata": {
                "analysis_date": self.analysis_date,
                "execution_time": time.time() - self.start_time,
                "token_usage": self.token_usage,
                "api_costs": self.calculate_costs(),
                "has_errors": bool(errors)
            }
        }
        
        # Store the final report in the state
        state["report"] = final_report
        logger.info("[[finalize]]: Created and stored final report")
        
        # Log and save the final markdown for review
        logger.info(f"[[finalize]]: Final Markdown Content:\n{final_report['report']}")
        
        # Save to a file for easier viewing
        output_path = 'output/final_report.md'
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(final_report['report'])
        logger.info(f"[[finalize]]: Saved final markdown to {output_path}")
        
        logger.info("[[finalize]]: Finalization complete")
        return state
        
    except Exception as e:
        print(f"ERROR [[_finalize_state]]: Error finalizing state: {str(e)}")
        if "errors" not in state:
            state["errors"] = []
        state["errors"].append(str(e))
        self._error = str(e)
        return state

def fix_citations(report):
    # Implement citation fixing logic here
    return report
