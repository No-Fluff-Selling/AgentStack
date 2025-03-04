from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict
from dataclasses import dataclass
import json
from langchain.schema import SystemMessage

@dataclass
class SourceDocument:
    """Document with source information for citation tracking."""
    content: str
    source_url: str
    source_type: str  # 'webpage' or 'news'
    metadata: Optional[Dict] = None

class BranchState(TypedDict):
    sitemap_urls: List[str]
    page_contents: Dict[str, str]
    raw_page_contents: List[str]
    news_data: Dict[str, Any]
    report: str
    table_name: str
    job_listings: List[Dict[str, Any]]  # Initialize job listings data

class GraphState(TypedDict):
    inputs: Dict[str, Any]
    messages: List[str]
    branches: Dict[str, BranchState]
    errors: Optional[List[str]]

class CustomJSONEncoder(json.JSONEncoder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.visited_objects = set()

    def default(self, obj):
        if isinstance(obj, SystemMessage):
            return {"type": "SystemMessage", "content": obj.content}

        try:
            if obj in self.visited_objects:
                return "[Circular Reference]"
        except TypeError:
            # If the object is unhashable, skip adding it to visited_objects
            return super().default(obj)

        try:
            # Attempt to hash the object to check if it's hashable
            hash(obj)
            self.visited_objects.add(obj)
        except TypeError:
            # If the object is unhashable, skip adding it to visited_objects
            pass

        if hasattr(obj, '__class__') and obj.__class__.__name__ == 'Results':
            print(f"DEBUG: CustomJSONEncoder encountered object of type {obj.__class__.__name__}")
            print(f"DEBUG: Object attributes: {obj.__dict__}")
            if not obj.__dict__:
                return {}  # Handle Results with empty attributes
            if hasattr(obj, 'results'):
                return {"type": "Results", "results": obj.results}
            return {"type": "Results", "data": str(obj)}
        
        if hasattr(obj, '__class__') and obj.__class__.__name__ == 'Result':
            print(f"DEBUG: CustomJSONEncoder encountered object of type {obj.__class__.__name__}")
            print(f"DEBUG: Object attributes: {obj.__dict__}")
            return {"type": "Result", "attributes": obj.__dict__}

        return super().default(obj)
