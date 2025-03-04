"""FastAPI integration for B2B Researcher Agent."""

import os
import sys
import logging

logger = logging.getLogger(__name__)

# Add src directory to Python path for all modules in this package
possible_project_roots = [
    # Development path (current structure)
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")),
    # Deployment path (when in Fly.io)
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")),
]

# Try each possible root until we find one with src/graph.py
for project_root in possible_project_roots:
    src_path = os.path.join(project_root, "src")
    graph_path = os.path.join(src_path, "graph.py")
    
    if os.path.exists(graph_path):
        if src_path not in sys.path:
            sys.path.append(src_path)
            logger.info(f"Added {src_path} to Python path")
        break
else:
    logger.error("Could not find src/graph.py in any of the possible project roots")