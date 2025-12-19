import os
from typing import Any

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langchain_core.documents import Document
from langgraph.prebuilt import create_react_agent
from langgraph.graph.message import MessagesState
from langgraph.checkpoint.memory import MemorySaver

from tools import TOOL_KIT

load_dotenv()


class Agent:
    def __init__(self, instructions: str, model: str = "gpt-4o-mini", temperature: float = 0.0):

        # Initialize the LLM
        llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            base_url="https://openai.vocareum.com/v1",
            api_key=os.getenv("VOCAREUM_API_KEY")
        )

        # Create the Energy Advisor agent
        self.graph = create_react_agent(
            messages_modifier=SystemMessage(content=instructions),
            model=llm,
            tools=TOOL_KIT,
            # interrupt_before=['tools'],  # NOTE: For debugging
            checkpointer=MemorySaver(),
        )
        self.graph.get_graph().draw_png('default_react_agent_graph.png')

    def invoke(self, question: str, context: str = None, thread_id: str = "default_thread") -> str:
        """
        Ask the Energy Advisor a question about energy optimization.
        
        Args:
            question (str): The user's question about energy optimization
            location (str): Location for weather and pricing data
        
        Returns:
            str: The advisor's response with recommendations
        """
        
        messages = []
        if context:
            # Add some context to the question as a system message
            messages.append(
                ("system", context)
            )
            
        config = {
            'recursion_limit': 100,
            'configurable':
            {
                'thread_id': thread_id,
                'electricity_pricing': {
                    'peak_hours': list(range(6, 19)),
                    'base_rate': 0.10,
                    'peak_rate': 0.15,
                }
            }
        }

        messages.append(
            ("user", question)
        )
        
        # Get response from the agent
        response = self.graph.invoke(
            input= {
                "messages": messages
            },
            config=config,
        )
        
        return response

    def get_agent_tools(self):
        """Get list of available tools for the Energy Advisor"""
        return [t.name for t in TOOL_KIT]

