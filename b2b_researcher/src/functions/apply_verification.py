from typing import List, Set
from langchain.docstore.document import Document
from langchain_community.vectorstores import FAISS

def apply_verification(self, docs: List[Document], vector_store: FAISS, 
                        config: dict, used_urls: set) -> List[Document]:
    """Perform verification passes based on config with strict limits"""
    try:
        required_sections = config.get('required_sections', [])
        max_attempts = min(config.get('max_attempts', 2), 2)  # Cap at 2 attempts
        docs_per_attempt = 3  # Allow more docs per verification attempt
        
        print(f"DEBUG [[Verification]]: Starting verification with {len(docs)} documents")
        print(f"DEBUG [[Verification]]: Required sections: {required_sections}")
        
        for attempt in range(max_attempts):
            # Verify coverage of required sections
            coverage_report = self.verify_coverage(docs, required_sections)
            coverage_percentage = coverage_report.coverage_ratio * 100
            
            print(f"\nDEBUG [[Verification]]: Attempt {attempt + 1}")
            print(f"DEBUG [[Verification]]: Current coverage: {coverage_percentage:.1f}%")
            print(f"DEBUG [[Verification]]: Missing sections: {coverage_report.missing}")
            
            if not coverage_report.missing or coverage_report.coverage_ratio >= 0.9:  # Stop at 90% coverage
                print("DEBUG [[Verification]]: Achieved sufficient coverage (≥90%), stopping verification")
                break
            
            # Retrieve missing aspects (all of them)
            query = f"Find information about: {', '.join(coverage_report.missing)}"
            print(f"DEBUG [[Verification]]: Querying for missing sections: {query}")
            
            new_docs = vector_store.similarity_search(query, k=docs_per_attempt)
            added_docs = [d for d in new_docs if d.metadata['source_url'] not in used_urls]
            
            print(f"DEBUG [[Verification]]: Found {len(added_docs)} new unique documents")
            docs.extend(added_docs)
            used_urls.update(d.metadata['source_url'] for d in added_docs)
        
        return docs
    except Exception as e:
        print(f"DEBUG [[Verification]]: Error in verification: {str(e)}")
        return docs  # Return original docs if verification fails