import agentstack
from src.types import GraphState

@agentstack.task
def initialize_state(self, state: GraphState) -> GraphState:
    """Initialize the graph state."""
    print("DEBUG [[initialize]]: Starting initialization")
    
    # Validate required inputs
    required_inputs = ["user_url", "target_url", "submission_id"]
    missing_inputs = [input_key for input_key in required_inputs if input_key not in state["inputs"]]
    if missing_inputs:
        raise ValueError(f"Missing required inputs: {', '.join(missing_inputs)}")
    
    # Store URLs and submission ID for later use
    self.user_url = state["inputs"]["user_url"]
    self.target_url = state["inputs"]["target_url"]
    self.submission_id = state["inputs"]["submission_id"]
    
    # Initialize branches if not present
    if "branches" not in state:
        state["branches"] = {}
    for branch in ["user", "target"]:
        if branch not in state["branches"]:
            state["branches"][branch] = {}
    
    # Initialize error tracking
    if "errors" not in state:
        state["errors"] = []
    
    print("DEBUG [[initialize]]: Initialization complete")
    return state
