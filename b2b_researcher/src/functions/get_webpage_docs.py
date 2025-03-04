from typing import List, Dict, Any
from src.types import GraphState
from langchain.docstore.document import Document

def get_webpage_docs(self, state: GraphState, branch: str) -> List[Document]:
    """Create webpage documents from raw page contents."""
    print(f"DEBUG [{branch}] [[get_webpage_docs]]: Starting webpage document creation")
    
    # Get raw content
    raw_content = state["branches"][branch].get("raw_page_contents", [])
    print(f"DEBUG [{branch}] [[get_webpage_docs]]: Checking raw_page_contents for branch: {branch}")
    print(f"DEBUG [{branch}] [[get_webpage_docs]]: Raw content type: {type(raw_content)}")
    print(f"DEBUG [{branch}] [[get_webpage_docs]]: raw_page_contents length: {len(raw_content)}")

    if not raw_content:
        print(f"DEBUG [{branch}] [[get_webpage_docs]]: raw_page_contents is empty")
        return []

    # Debug first item
    first_item = raw_content[0]
    print(f"DEBUG [{branch}] [[get_webpage_docs]]: First raw_page_contents item type: {type(first_item)}")
    print(f"DEBUG [{branch}] [[get_webpage_docs]]: First raw_page_contents item keys: {list(first_item.__dict__.keys())}")
    print(f"DEBUG [{branch}] [[get_webpage_docs]]: Sample first item text: {getattr(first_item, 'text', '')[:200]}")

    webpage_docs = []
    for page in raw_content:
        # Create metadata dictionary
        metadata = {
            "title": getattr(page, "title", None),
            "published_date": getattr(page, "published_date", None),
            "author": getattr(page, "author", None),
            "score": getattr(page, "score", None),
            "summary": getattr(page, "summary", None),
            "source_url": getattr(page, "url", ""),  # Ensure we're using the specific page URL
            "source_type": "webpage"
        }
        # Filter out None values
        metadata = {k: v for k, v in metadata.items() if v is not None}
        
        # Debug the URL to ensure it's the specific page URL, not just the base URL
        print(f"DEBUG [{branch}] [[get_webpage_docs]]: Using source_url: {metadata.get('source_url', 'None')}")
        
        # Create Document
        doc = Document(
            page_content=getattr(page, "text", ""),
            metadata=metadata
        )
        webpage_docs.append(doc)
    
    print(f"DEBUG [{branch}] [[get_webpage_docs]]: Created {len(webpage_docs)} webpage documents")
    return webpage_docs