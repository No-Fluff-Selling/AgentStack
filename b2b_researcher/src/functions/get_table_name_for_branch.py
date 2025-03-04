from typing import Dict, Any

def get_table_name_for_branch(self, branch: str, data_type: str) -> str:
    """Generate consistent table name for a branch and data type."""
    print(f"DEBUG [[get_table_name_for_branch]]: Generating table name for branch '{branch}' and data type '{data_type}'")
    
    if not hasattr(self, 'user_url') or not hasattr(self, 'target_url'):
        print(f"ERROR [[get_table_name_for_branch]]: URLs not initialized")
        return ""
        
    url = self.user_url if branch == "user" else self.target_url
    if not url:
        print(f"ERROR [[get_table_name_for_branch]]: No URL found for branch {branch}")
        return ""
        
    safe_url = self.escape(url)
    safe_url = safe_url.replace("https://", "").replace("http://", "").replace("/", "_").replace(".", "_")
    table_name = f"{safe_url}_{data_type}_{branch}"
    print(f"DEBUG [[get_table_name_for_branch]]: Generated table name: {table_name}")
    return table_name