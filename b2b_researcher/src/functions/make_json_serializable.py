import json
from typing import Any, Dict, List, Union

def make_json_serializable(self, obj: Union[Any, Dict, List], depth: int = 0) -> Union[Any, Dict, List, str]:
    """Make an object JSON serializable by converting non-serializable parts to strings."""
    max_depth = 5
    if depth > max_depth:
        return f"Recursion depth exceeded (max={max_depth})"

    if isinstance(obj, dict):
        return {k: self.make_json_serializable(v, depth + 1) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [self.make_json_serializable(item, depth + 1) for item in obj]
    elif hasattr(obj, 'to_dict'):  # Handle objects with to_dict method
        return obj.to_dict()
    elif hasattr(obj, '__dict__'):  # Handle objects with __dict__
        return str(obj)
    else:
        try:
            json.dumps(obj)  # Check if already JSON serializable
            return obj
        except (TypeError, OverflowError):
            return str(obj)  # Convert to string if not serializable