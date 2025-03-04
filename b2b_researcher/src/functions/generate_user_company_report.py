from typing import List, Dict, Any
from src.types import GraphState
from langchain.docstore.document import Document
from langchain.schema import SystemMessage
from src.prompts.user_report_templates import (
    USER_REPORT_TEMPLATE,
    USER_VERIFICATION_PROMPT,
    USER_FOCUS_AREAS
)

def generate_user_company_report(self, state: GraphState) -> str:
    """Generate a report about the user's company."""
    try:
        print("DEBUG [[generate_user_company_report]]: Creating documents for user company report")
        
        # Get webpage docs - we only need webpage data for user company analysis
        # Check if documents are already available in state
        if "user_webpage_docs" in state:
            print("DEBUG [[generate_user_company_report]]: Using pre-created webpage documents from state")
            webpage_docs = state["user_webpage_docs"]
        else:
            webpage_docs = self.get_webpage_docs(state, "user")
            # Store documents in state to avoid redundant creation
            state["user_webpage_docs"] = webpage_docs
            print(f"DEBUG [[generate_user_company_report]]: Created and stored {len(webpage_docs)} webpage documents")
        
        # Get company name from URL
        company_url = state["inputs"].get("user_url", "")
        company_name = self.get_company_name_from_url(company_url)
        
        # Execute RAG process with Deepseek R1 model
        report, source_metadata = self.execute_rag_process(
            webpage_docs=webpage_docs,
            news_docs=[],  # No news needed for user company analysis
            company_name=company_name,
            key_sections=USER_FOCUS_AREAS,
            verification_prompt=USER_VERIFICATION_PROMPT,
            report_template=USER_REPORT_TEMPLATE,
            state=state,
            branch="user",
            model="deepseek-r1"  # Specify to use Deepseek R1 model
        )
        
        ## Validate report content
        #is_valid, validation_msg = self.validate_user_report_content(report, company_name)
        #if not is_valid:
        #    print(f"WARNING: Report validation failed for user company {company_name}")
        #    print(f"Validation errors:\n{validation_msg}")
        #    state["messages"].append(SystemMessage(content="[user] Warning: Generated report may be missing some key information"))
        
        print("==============================================================================================")
        print("==============================================================================================")
        print("User Company Report before citations:\n", report)
        
        # Fix citations
        report = self.fix_citation_sequence(report, source_metadata)
        
        # Strip markdown code block markers if present
        report = self._strip_markdown_code_blocks(report)
        
        print("User Company Report after citations:\n", report)
        
        # Store template variables and metadata in state for potential later use
        state["user_report_data"] = {
            "company_name": company_name,
            "webpage_context": "\n\n".join([
                f"{d.page_content} [Citation: {source_metadata.get(d.metadata.get('source_url'), {}).get('index', '?')}]" 
                for d in webpage_docs 
                if d.metadata.get('source_url') and d.metadata.get('source_url') in source_metadata
            ]),
            "citations": "<br>\n".join([
                f"[{metadata['index']}]. [{metadata['title']}]({url}) - {url}"
                for url, metadata in sorted(source_metadata.items(), key=lambda x: x[1]['index'])
            ]) + "<br>",
            "source_metadata": source_metadata
        }
        
        # Save report to state
        state["branches"]["user"]["report"] = report
        
        # Save to database if configured
        self.save_company_report_to_db(state, "user")
        
        print("DEBUG [[generate_user_company_report]]: User company report generation completed")
        return report
    except Exception as e:
        print(f"ERROR [[generate_user_company_report]]: Error generating user company report: {str(e)}")
        raise