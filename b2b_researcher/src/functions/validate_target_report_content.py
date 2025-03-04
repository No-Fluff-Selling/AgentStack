"""
Validate the content of a target company report.
"""
import re
import json
from typing import Dict, Any, List, Tuple
from langchain_community.chat_models import ChatOpenAI
from src.prompts.target_report_templates import (
    TARGET_REQUIRED_SECTIONS,
    TARGET_VERIFICATION_PROMPT
)

def validate_target_report_content(self, report_text: str, company_name: str, user_company_name: str) -> Tuple[bool, str]:
    """Validate if the target company report contains all critical elements for sales."""
    # Programmatic validation first
    validation_errors = []
    
    # Check for required sections
    for section in TARGET_REQUIRED_SECTIONS:
        if section not in report_text:
            validation_errors.append(f"Missing required section: {section}")
    
    # Validate Decision Makers section
    decision_makers_section = re.search(r'## Decision Makers to Approach\n(.*?)(?=##|\Z)', report_text, re.DOTALL)
    if decision_makers_section:
        dm_content = decision_makers_section.group(1)
        if not re.search(r'\[\d+\]', dm_content):
            validation_errors.append("Decision Makers section present but lacks citations")
    
    # Check citation format and sequence
    citations = re.findall(r'\[(\d+)\]', report_text)
    if not citations:
        validation_errors.append("No citations found in the report")
    else:
        # Convert to integers and check sequence
        try:
            citation_numbers = [int(c) for c in citations]
            expected_sequence = list(range(1, max(citation_numbers) + 1))
            if citation_numbers != sorted(citation_numbers) or set(citation_numbers) != set(expected_sequence):
                validation_errors.append("Citations are not properly sequenced or have gaps")
        except ValueError:
            validation_errors.append("Invalid citation format found")
    
    # Check citation section format
    citations_section = re.search(r'## Citations\n(.*?)(?=##|\Z)', report_text, re.DOTALL)
    if not citations_section:
        validation_errors.append("Citations section not found or improperly formatted")
    else:
        citation_entries = re.findall(r'\[(\d+)\]\. \[(.*?)\]\((http[s]?://\S+)\)', citations_section.group(1))
        if not citation_entries:
            validation_errors.append("Citations section does not contain properly formatted citations")
        
        # Verify all citations are used in the text
        text_citations = set(citations)
        reference_citations = {str(i+1) for i in range(len(citation_entries))}
        if text_citations != reference_citations:
            validation_errors.append("Mismatch between citations used in text and citations listed in References")
    
    if validation_errors:
        error_msg = "\n".join(validation_errors)
        return False, error_msg
    
    # Content validation through LLM
    messages = [
        {
            "role": "developer",
            "content": "You are a strict report validator specializing in verifying sales intelligence reports for accuracy, completeness, and proper citation."
        },
        {
            "role": "user",
            "content": TARGET_VERIFICATION_PROMPT.format(
                report_text=report_text,
                user_company_name=user_company_name
            )
        }
    ]
    
    try:
        response = self.track_chat_completion("target", messages)
        if response.startswith("PASS"):
            return True, ""
        else:
            return False, response
    except Exception as e:
        return False, f"Error during validation: {str(e)}"