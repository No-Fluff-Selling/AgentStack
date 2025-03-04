import agentstack
from src.types import GraphState

@agentstack.task
def wrap_node(self, node_func):
    """Wrap a node function with error handling and state tracking."""
    def wrapped(state: GraphState) -> GraphState:
        try:
            self._state = state  # Track current state
            result = node_func(state)
            self._state = result  # Update state after successful execution
            return result
        except Exception as e:
            print(f"ERROR: Node execution failed: {str(e)}")
            if "errors" not in state:
                state["errors"] = []
            state["errors"].append(str(e))
            self._error = str(e)
            return state
    return wrapped
