import agentstack
from src.types import GraphState

@agentstack.task
def merge_branch_states(self, base_state: GraphState, scraping_state: GraphState, news_state: GraphState, branch: str) -> GraphState:
    """Helper method to merge states from different branch operations."""
    # Merge scraping state
    if "branches" in scraping_state and branch in scraping_state["branches"]:
        scraping_branch = scraping_state["branches"][branch]
        # Preserve raw_page_contents and other data
        for key, value in scraping_branch.items():
            if value is not None:  # Only update if value exists
                base_state["branches"][branch][key] = value
        print(f"DEBUG [{branch}] [[merge_branch_states]]: Merged scraping state with {len(scraping_branch.get('raw_page_contents', []))} raw_page_contents")

    # Merge news state
    if "branches" in news_state and branch in news_state["branches"]:
        news_branch = news_state["branches"][branch]
        # Only merge news data to avoid overwriting scraping data
        if "news_data" in news_branch:
            base_state["branches"][branch]["news_data"] = news_branch["news_data"]

    return base_state
