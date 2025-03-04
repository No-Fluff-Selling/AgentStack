from typing import List, Dict
from langchain.docstore.document import Document

def should_continue_retrieval(self, batch_docs: List[Document], iteration: int, 
                            max_iters: int, config: dict) -> bool:
    """Decision logic for early termination"""
    # Configurable thresholds
    min_new_docs = config.get('min_new_docs', 2)
    redundancy_threshold = config.get('redundancy_pct', 0.7)
    
    if iteration >= max_iters - 1:
        return False
    if len(batch_docs) < min_new_docs:
        return False
    
    # Calculate content redundancy
    unique_content = len({d.page_content[:100] for d in batch_docs})
    if unique_content / len(batch_docs) < redundancy_threshold:
        return False
        
    return True