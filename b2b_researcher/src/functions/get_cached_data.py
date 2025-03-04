from typing import Dict, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

def get_cached_data(self, table_name: str, url_column: str, url: str) -> Optional[Dict]:
    """Retrieve cached data from Neon database for a specific URL."""
    if not self.enable_db_save:
        print(f"DEBUG [[get_cached_data]]: Database operations disabled, skipping cache lookup for URL '{url}'")
        return None
        
    print(f"DEBUG [[get_cached_data]]: Retrieving data from table '{table_name}' for URL '{url}'")
    
    if not table_name or not url_column or not url:
        print("ERROR [[get_cached_data]]: Missing required parameters")
        return None
        
    try:
        with self.get_db_connection() as conn:
            with conn.cursor() as cur:
                query = f"""
                    SELECT 
                        id,
                        url,
                        title,
                        text,
                        summary,
                        published_date,
                        author,
                        created_at,
                        analysis_date
                    FROM {table_name}
                    WHERE {url_column} = %s
                    ORDER BY created_at DESC
                    LIMIT 1;
                """
                print(f"DEBUG [[get_cached_data]]: Executing query with URL: {url}")
                cur.execute(query, (url,))
                result = cur.fetchone()
                
                if result:
                    print(f"DEBUG [[get_cached_data]]: Found cached data for URL '{url}'")
                    # Convert row to dictionary
                    columns = ['id', 'url', 'title', 'text', 'summary', 'published_date', 
                                'author', 'created_at', 'analysis_date']
                    data = {columns[i]: result[i] for i in range(len(columns))}
                    return data
                else:
                    print(f"DEBUG [[get_cached_data]]: No cached data found for URL '{url}'")
                    return None
            
    except Exception as e:
        print(f"ERROR [[get_cached_data]]: Error retrieving cached data: {str(e)}")
        return None