from typing import Annotated
from typing_extensions import TypedDict

from langchain.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_openai import ChatOpenAI


import agentstack


class State(TypedDict):
    inputs: dict[str, str]
    messages: Annotated[list, add_messages]


class B2bresearcherGraph:

    @agentstack.task
    def scrape_single_page(self, state: State):
        task_config = agentstack.get_task('scrape_single_page')
        messages = ChatPromptTemplate.from_messages([
            ("user", task_config.prompt), 
        ])
        messages = messages.format_messages(**state['inputs'])
        return {'messages': messages + state['messages']}

    @agentstack.agent
    def web_scraper(self, state: State):
        agent_config = agentstack.get_agent('web_scraper')
        messages = ChatPromptTemplate.from_messages([
            ("user", agent_config.prompt), 
        ])
        messages = messages.format_messages(**state['inputs'])
        agent = ChatOpenAI(model=agent_config.model)
        # Filter firecrawl tools to only use web_scrape
        firecrawl_tools = [tool for tool in agentstack.tools['firecrawl'] if tool.__name__ == 'web_scrape']
        agent = agent.bind_tools([*firecrawl_tools, *agentstack.tools['exa'], *agentstack.tools['perplexity']])
        response = agent.invoke(
            messages + state['messages'],
        )
        return {'messages': [response, ]}

    def run(self, inputs: list[str]):
        # Filter firecrawl tools to only use web_scrape
        firecrawl_tools = [tool for tool in agentstack.tools['firecrawl'] if tool.__name__ == 'web_scrape']
        tools = ToolNode([*firecrawl_tools, *agentstack.tools['exa'], *agentstack.tools['perplexity']])
        self.graph = StateGraph(State)
        self.graph.add_edge(START, "scrape_single_page")
        self.graph.add_edge("scrape_single_page", "web_scraper")
        self.graph.add_edge("web_scraper", END)
        
        self.graph.add_conditional_edges("web_scraper", tools_condition)
        self.graph.add_edge("tools", "web_scraper")
        self.graph.add_node("scrape_single_page", self.scrape_single_page)
        self.graph.add_node("web_scraper", self.web_scraper)
        self.graph.add_node("tools", tools)
        

        app = self.graph.compile()
        result_generator = app.stream({
            'inputs': inputs,
            'messages': [],
        })

        for message in result_generator:
            for k, item in message.items():
                for m in item['messages']:
                    agentstack.log.notify(f"\n\n{k}:")
                    agentstack.log.info(m.content)

