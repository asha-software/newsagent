from pprint import pprint
import json
from IPython.display import Image, display
from dotenv import load_dotenv
import importlib
import os
import sys

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing import Annotated, TypedDict, List, Dict, Any

project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import core.tools.registry

MODEL = "mistral-nemo"
TEMPERATURE = 0
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(os.path.dirname(script_dir), '.env'), override=True)
PATH_TO_FILE = os.path.abspath(__file__)


TOOL_REGISTRY = {
    'core.tools.builtins.calculator': ['multiply', 'add', 'divide'],
    'core.tools.builtins.wikipedia': ['query']
}


def import_function(module_name, function_name):
    """Dynamically imports a function from a module."""
    try:
        module = importlib.import_module(module_name)
        function = getattr(module, function_name)
        return function
    except (ImportError, AttributeError) as e:
        print(f"Error: Could not import function '{function_name}' from module '{module_name}'.")
        print(f"Exception: {e}")
        return None

all_tools = [import_function(module, function) for module,
         functions in TOOL_REGISTRY.items() for function in functions]
print(f"Tools: {[tool.__name__ for tool in all_tools]}")


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    claim: str
    used_tools: List[str]
    evidence: list[dict]

script_dir = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(script_dir, 'prompts/research_agent_system_prompt.txt'), 'r') as f:
    sys_msg = SystemMessage(content=f.read())


def preprocessing(state: State):
    """
    Preprocesses state before sending to the assistant for tool routing.
    """
    state['messages'] = [sys_msg, HumanMessage(content=state['claim'])]
    state['used_tools'] = []
    state['evidence'] = []
    return state


def assistant(state: State) -> State:
    """
    The main assistant node that processes the claim and decides which tools to use.
    This leverages LangChain/LangGraph's built-in tool calling logic.
    """
    llm_with_tools = ChatOllama(
        model=MODEL,
        temperature=TEMPERATURE,
    ).bind_tools(all_tools)
    
    response = llm_with_tools.invoke(state['messages'])
    
    if hasattr(response, 'tool_calls'):
        for tool_call in response.tool_calls:
            tool_name = tool_call['name']
            if tool_name not in state['used_tools']:
                state['used_tools'].append(tool_name)
    
    return {"messages": response}


def postprocessing(state: State) -> State:
    """
    Extract evidence from the message history.
    """
    evidence = []
    for i in range(len(state['messages'])):
        message = state['messages'][i]
        if isinstance(message, AIMessage) and hasattr(message, 'tool_calls'):
            for tool_call in message.tool_calls:
                for j in range(i + 1, len(state['messages'])):
                    next_message = state['messages'][j]
                    if isinstance(next_message, ToolMessage) and next_message.tool_call_id == tool_call['id']:
                        evidence.append({
                            'name': tool_call['name'],
                            'args': tool_call['args'],
                            'result': next_message.content
                        })
                        break
    
    state['evidence'] = evidence
    return state


builder = StateGraph(State)
builder.add_node("preprocessing", preprocessing)
builder.add_node("assistant", assistant)
builder.add_node("tools", ToolNode(all_tools))
builder.add_node("postprocessing", postprocessing)
builder.add_edge(START, "preprocessing")
builder.add_edge("preprocessing", "assistant")
builder.add_conditional_edges(
    "assistant",
    tools_condition,
    {
        "tools": "tools",
        "__end__": "postprocessing"
    }
)
builder.add_edge("tools", "assistant")
builder.add_edge("postprocessing", END)

agent = builder.compile()

if __name__ == "__main__":
    factual_claim = "Albert Einstein developed the theory of relativity"
    factual_result = agent.invoke({"claim": factual_claim})
    
    print("\nFactual Claim Test:")
    print(f"Claim: {factual_claim}")
    print("Tools Used:")
    for tool_name in factual_result.get('used_tools', []):
        print(f"  {tool_name}")
    
    print("Evidence:")
    for evidence in factual_result.get('evidence', []):
        print(f"  Tool: {evidence['name']}")
        print(f"  Args: {evidence['args']}")
        print(f"  Result: {evidence['result'][:100]}..." if len(evidence['result']) > 100 else f"  Result: {evidence['result']}")
        print()
    
    math_claim = "12 multiplied by 10 equals 120"
    math_result = agent.invoke({"claim": math_claim})
    
    print("\nMathematical Claim Test:")
    print(f"Claim: {math_claim}")
    print("Tools Used:")
    for tool_name in math_result.get('used_tools', []):
        print(f"  {tool_name}")
    
    print("Evidence:")
    for evidence in math_result.get('evidence', []):
        print(f"  Tool: {evidence['name']}")
        print(f"  Args: {evidence['args']}")
        print(f"  Result: {evidence['result']}")
        print()
