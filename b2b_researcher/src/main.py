#!/usr/bin/env python
import sys
from graph import B2bresearcherGraph
import agentstack
import agentops

agentops.init(default_tags=agentstack.get_tags())

instance = B2bresearcherGraph()

def run():
    """
    Run the agent.
    """
    instance.run(inputs=agentstack.get_inputs())


if __name__ == '__main__':
    run()