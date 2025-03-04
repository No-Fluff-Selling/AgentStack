#!/usr/bin/env python3
"""
Test script to verify the report generation process and document creation redundancy fixes.
"""

import os
import sys
import logging
from src.graph import B2bresearcherGraph

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_report_generation():
    """Test the report generation process with the redundancy fixes."""
    # Create a graph instance with database saving disabled
    graph = B2bresearcherGraph(enable_db_save=False)
    
    # Define test inputs
    inputs = {
        "user_url": "https://codeium.com",
        "target_url": "https://anthropic.com",
        "user_name": "Test User",
        "user_email": "test@example.com",
        "user_company": "Codeium",
        "target_company": "Anthropic",
        "user_role": "Developer"
    }
    
    # Run the graph
    try:
        print("Starting graph execution...")
        result = graph.run(inputs)
        
        # Check if the reports were generated
        if "target_company_report" in result:
            print("\n\nTarget company report generated successfully!")
            print(f"Report length: {len(result['target_company_report'])} characters")
        else:
            print("Target company report was not generated.")
        
        if "branches" in result and "user" in result["branches"] and "report" in result["branches"]["user"]:
            print("\n\nUser company report generated successfully!")
            print(f"Report length: {len(result['branches']['user']['report'])} characters")
        else:
            print("User company report was not generated.")
        
        # Print usage report
        graph.print_usage_report()
        
        return True
    except Exception as e:
        print(f"Error during graph execution: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing report generation with redundancy fixes...")
    success = test_report_generation()
    sys.exit(0 if success else 1)
