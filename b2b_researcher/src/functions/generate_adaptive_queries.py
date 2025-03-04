import re
from typing import List
from langchain.docstore.document import Document
from src.prompts.target_report_templates import TARGET_FOCUS_AREAS
from src.prompts.user_report_templates import USER_FOCUS_AREAS

def generate_adaptive_queries(self, collected_docs: List[Document], n_queries: int, branch: str, company_name: str) -> List[str]:
    """Generate follow-up queries based on collected documents and branch type.
    
    Args:
        collected_docs: List of documents collected so far
        n_queries: Number of queries to generate
        branch: Branch type ('user' or 'target')
        company_name: Name of the company being analyzed
        
    Returns:
        List of generated queries
    """
    try:
        # Extract key sections based on branch type
        if branch == "target":
            key_sections = TARGET_FOCUS_AREAS
        else:  # user branch
            key_sections = USER_FOCUS_AREAS
        
        # Prepare document content
        doc_texts = []
        for doc in collected_docs[-5:]:  # Use last 5 docs to avoid token limits
            source = doc.metadata.get('source_url', '')
            content = doc.page_content[:300]  # Limit content length
            doc_texts.append(f"Source: {source}\nContent: {content}\n")

        # Create prompt for generating queries
        if branch == "target":
            prompt = f"""You are a B2B sales intelligence specialist. Review these documents about a potential client company and generate specific questions to gather sales-relevant information.

Documents:
{chr(10).join(doc_texts)}

Focus on finding information about:
{", ".join(key_sections)}

Generate {n_queries} specific questions that will help understand:
{chr(10).join(f"{i+1}. {area}" for i, area in enumerate(key_sections))}

Format each question on a new line. Questions should be specific and targeted."""
        else:  # user branch
            prompt = f"""You are a B2B product specialist. Review these documents about {company_name} and generate specific questions to gather comprehensive product and capability information.

Documents:
{chr(10).join(doc_texts)}

Focus on finding information about:
{", ".join(key_sections)}

Generate {n_queries} specific questions that will help understand:
{chr(10).join(f"{i+1}. {area}" for i, area in enumerate(key_sections))}

Format each question on a new line. Questions should be specific and targeted."""
        
        # Generate queries using chat completion
        messages = [
            {
                "role": "developer",
                "content": "You are an adaptive research strategist specializing in business intelligence. Your role is to analyze existing research and generate targeted follow-up queries that fill knowledge gaps and deepen understanding of key business aspects."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        response = self.track_chat_completion(
            "system",
            messages
        )
        
        # Split response into individual queries
        queries = [q.strip() for q in response.split('\n') if q.strip()]
        
        # Filter out any non-query lines (e.g. headers, footers)
        queries = [re.sub(r'^\d+\.\s*', '', q) for q in queries if re.match(r'^\d+\.', q)]
        
        return queries[:n_queries]
        
    except Exception as e:
        print(f"Error generating adaptive queries: {str(e)}")
        return self.generate_fallback_queries(n_queries, branch)