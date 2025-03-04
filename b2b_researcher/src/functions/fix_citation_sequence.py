from typing import Dict, Any, Union
import re

def fix_citation_sequence(report: str, source_metadata: Dict[str, Dict[str, Union[str, int]]]) -> str:
    """Post-process report to fix citation numbering and formatting.
    
    Args:
        report: The full report text
        source_metadata: Dictionary mapping URLs to metadata including citation indices
        
    Returns:
        Updated report with fixed citation sequence
    """
    try:
        print(f"DEBUG [[fix_citation_sequence]]: Starting citation renumbering")
        
        # Step 1: Find all citation numbers used in the report
        # Update regex to match [X] or X format citations
        citation_pattern = r'\[(\d+)\]'
        used_citations = re.findall(citation_pattern, report)
        
        # Check for potential citations without brackets
        alternate_pattern = r'(?<!\[)(\d+)(?!\])'
        potential_citations = re.findall(alternate_pattern, report)
        
        # Filter out false positives that are likely not citations
        # (only include if they match known source indices)
        valid_indices = {data["index"] for data in source_metadata.values()}
        additional_citations = [c for c in potential_citations 
                              if int(c) in valid_indices]
        
        # Combine all citations
        used_citations.extend(additional_citations)
        used_citation_indices = set([int(c) for c in used_citations])
        
        print(f"DEBUG [[fix_citation_sequence]]: Found {len(used_citation_indices)} unique citations in report")
        
        # Step 2: Create mapping from old to new citation numbers
        citation_map = {old_idx: new_idx + 1 
                        for new_idx, old_idx in enumerate(sorted(used_citation_indices))}
        
        # Step 3: Replace in-text citations with new numbers and make them hyperlinks
        def replace_citation(match):
            old_num = int(match.group(1))
            if old_num not in citation_map:
                return match.group(0)  # Return the original if not in our map
            
            new_num = citation_map[old_num]
            
            # Find the URL for this citation
            source_url = "#"
            for url, data in source_metadata.items():
                if data.get("index") == old_num:
                    source_url = url
                    break
                    
            return f'<a href="{source_url}" target="_blank">[{new_num}]</a>'
        
        text_with_fixed_citations = re.sub(citation_pattern, replace_citation, report)
        
        # Step 4: Create new Citations section with only used sources
        citations_section = re.search(r'## Citations\n(.*?)(?=##|\Z)', text_with_fixed_citations, re.DOTALL)
        if citations_section:
            # Extract current Citations section
            old_citations = citations_section.group(0)
            
            # Create new Citations section
            new_citations = "## Citations\n"
            # Add sources used count
            new_citations += f"{len(used_citation_indices)} sources used out of {len(source_metadata)} total sources.\n\n"
            
            # Add each used citation with new numbering
            used_source_metadata = sorted(
                [(url, data) for url, data in source_metadata.items() 
                 if data["index"] in used_citation_indices],
                key=lambda x: citation_map[x[1]["index"]]
            )
            
            for url, metadata in used_source_metadata:
                new_num = citation_map[metadata["index"]]
                title = metadata.get("title", "Source")
                # Format citation: only hyperlink the number, followed by title and then hyperlinked URL
                new_citations += f'<a href="{url}" target="_blank">[{new_num}]</a> {title} - <a href="{url}" target="_blank">{url}</a><br>\n'
            
            # Replace old Citations section with new one
            text_with_fixed_citations = text_with_fixed_citations.replace(old_citations, new_citations)
            
            print(f"DEBUG [[fix_citation_sequence]]: Successfully replaced Citations section")
        else:
            print(f"WARNING [[fix_citation_sequence]]: Could not find Citations section in report")
        
        return text_with_fixed_citations
        
    except Exception as e:
        print(f"ERROR [[fix_citation_sequence]]: Error fixing citations: {str(e)}")
        # Return original report if something goes wrong
        return report