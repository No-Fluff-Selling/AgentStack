from typing import List, Dict, Any
from langchain.docstore.document import Document
from langchain_community.chat_models import ChatOpenAI
import json

def verify_coverage(self, docs: List[Document], required_sections: List[str]):
    """Verify coverage of required sections"""
    try:
        # Create a prompt to analyze coverage
        doc_content = "\n\n".join([d.page_content[:200] + "..." for d in docs])
        sections_list = "\n".join(f"- {section}" for section in required_sections)
        
        messages = [
            {
                "role": "developer",
                "content": "You are a content coverage analyst specialized in evaluating business documents. Your role is to systematically assess if each required section is adequately covered in the provided content, ensuring comprehensive business reporting."
            },
            {
                "role": "user",
                "content": f"""Analyze the following company information and determine which of the required sections for a sales-focused report are adequately covered.

Company Information:
{doc_content}

Required Sections:
{sections_list}

For each section, respond with either "covered" or "missing" in a simple format:
section_name: covered/missing

Only include the status lines, nothing else."""
            }
        ]
        
        response = self.track_chat_completion("system", messages)

        # Parse response
        coverage = {}
        missing = []
        for line in response.strip().split('\n'):
            if ':' in line:
                section, status = line.split(':', 1)
                section = section.strip()
                status = status.strip().lower()
                coverage[section] = (status == 'covered')
                if status != 'covered':
                    missing.append(section)
        
        # Calculate coverage ratio
        covered = len([s for s in coverage.values() if s])
        total = len(required_sections)
        coverage_ratio = covered / total if total > 0 else 1.0
        
        return type('CoverageReport', (), {
            'coverage': coverage,
            'missing': missing,
            'coverage_ratio': coverage_ratio
        })()
    except Exception as e:
        print(f"DEBUG [[Verification]]: Error in verify_coverage: {str(e)}")
        return type('CoverageReport', (), {
            'coverage': {},
            'missing': required_sections,
            'coverage_ratio': 0.0
        })()