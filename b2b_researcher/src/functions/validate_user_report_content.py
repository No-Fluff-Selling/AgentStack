"""
Validate the content of a user company report.
"""
import re
import json
from typing import Dict, Any, List, Tuple
from langchain_community.chat_models import ChatOpenAI
from src.prompts.user_report_templates import (
    USER_REQUIRED_SECTIONS,
    USER_VERIFICATION_PROMPT
)

def validate_user_report_content(self, report_text: str, company_name: str) -> Tuple[bool, str]:
    """Validate if the user company report contains all critical elements and proper citations."""
    # Programmatic validation first
    validation_errors = []
    
    # Check for required sections
    for section in USER_REQUIRED_SECTIONS:
        if section.lower() not in report_text.lower():
            validation_errors.append(f"Missing required section: {section}")
    
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
    
    if validation_errors:
        error_msg = "\n".join(validation_errors)
        return False, error_msg
    
    # Content validation through LLM
    messages = [
        {
            "role": "developer",
            "content": "You are a strict report validator specializing in ensuring factual accuracy and proper citation in business research reports."
        },
        {
            "role": "user",
            "content": USER_VERIFICATION_PROMPT.format(
                report_text=report_text
            )
        }
    ]
    
    try:
        response = self.track_chat_completion("system", messages)
        if response.startswith("PASS"):
            return True, ""
        else:
            return False, response
    except Exception as e:
        return False, f"Error during validation: {str(e)}"