from typing import List, Dict, Any
from src.types import GraphState
from langchain.docstore.document import Document

def get_news_docs(self, state: GraphState, branch: str) -> List[Document]:
    """Create news documents from raw news content."""
    print(f"DEBUG [{branch}] [[get_news_docs]]: Starting news document creation")
    
    # Get raw content
    raw_content = state["branches"][branch].get("news_data", {}).get("main", [])
    print(f"DEBUG [{branch}] [[get_news_docs]]: Checking news_data for branch: {branch}")
    print(f"DEBUG [{branch}] [[get_news_docs]]: Raw content type: {type(raw_content)}")
    print(f"DEBUG [{branch}] [[get_news_docs]]: news_data length: {len(raw_content)}")

    if not raw_content:
        print(f"DEBUG [{branch}] [[get_news_docs]]: news_data is empty")
        return []

    # Debug first item
    first_item = raw_content[0]
    print(f"DEBUG [{branch}] [[get_news_docs]]: First news_data item type: {type(first_item)}")
    print(f"DEBUG [{branch}] [[get_news_docs]]: First news_data item keys: {list(first_item.keys() if isinstance(first_item, dict) else first_item.__dict__.keys())}")
    print(f"DEBUG [{branch}] [[get_news_docs]]: Sample first item text: {first_item.get('text', '') if isinstance(first_item, dict) else getattr(first_item, 'text', '')[:200]}")

    news_docs = []
    for article in raw_content:
        # Create metadata dictionary
        if isinstance(article, dict):
            metadata = {
                "title": article.get("title"),
                "published_date": article.get("published_date"),
                "author": article.get("author"),
                "score": article.get("score"),
                "summary": article.get("summary"),
                "source_url": article.get("url", ""),
                "source_type": "news"
            }
            text = article.get("text", "")
        else:
            metadata = {
                "title": getattr(article, "title", None),
                "published_date": getattr(article, "published_date", None),
                "author": getattr(article, "author", None),
                "score": getattr(article, "score", None),
                "summary": getattr(article, "summary", None),
                "source_url": getattr(article, "url", ""),
                "source_type": "news"
            }
            text = getattr(article, "text", "")

        # Filter out None values
        metadata = {k: v for k, v in metadata.items() if v is not None}
        
        # Create Document
        doc = Document(
            page_content=text,
            metadata=metadata
        )
        news_docs.append(doc)
    
    print(f"DEBUG [{branch}] [[get_news_docs]]: Created {len(news_docs)} news documents")
    return news_docs