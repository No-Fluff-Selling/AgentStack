from typing import List, Dict, Any, Optional, Union

def format_job_listings(self, job_listings):
    """Format job listings into a readable summary."""
    if not job_listings:
        return "No job listings found."
    
    summary = []
    for job in job_listings:
        if isinstance(job, dict):
            title = job.get("title", "Untitled")
            location = job.get("location", "No location specified")
            summary.append(f"- {title} ({location})")
    
    return "\n".join(summary) if summary else "No job listings found."