from typing import List
from src.prompts.target_report_templates import TARGET_FALLBACK_QUERIES
from src.prompts.user_report_templates import USER_FALLBACK_QUERIES

def generate_fallback_queries(self, n: int, branch: str):
    """Generate fallback queries if adaptive query generation fails"""
    if branch == "target":
        queries = TARGET_FALLBACK_QUERIES
    else:  # user branch
        queries = USER_FALLBACK_QUERIES
    return queries[:n]