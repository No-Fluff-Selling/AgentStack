#!/usr/bin/env python
import sys
import argparse
from src.graph import B2bresearcherGraph
import agentstack
import agentops

def parse_args():
    parser = argparse.ArgumentParser(description='Run the B2B researcher agent')
    parser.add_argument('--no-db-save', action='store_true', default=False,
                      help='Disable saving to database (default: False, saving enabled)')
    return parser.parse_args()

agentops.init(default_tags=agentstack.get_tags())

def run():
    """
    Run the agent.
    """
    args = parse_args()
    instance = B2bresearcherGraph(enable_db_save=not args.no_db_save)
    inputs = agentstack.get_inputs()
    for _ in instance.run(inputs=inputs):
        pass

if __name__ == '__main__':
    run()