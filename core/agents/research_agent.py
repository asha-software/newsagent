
from pprint import pprint
from IPython.display import Image, display
from dotenv import load_dotenv
import importlib
import os
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing import Annotated, TypedDict


MODEL = "mistral-nemo"
TEMPERATURE = 0
load_dotenv('../.env', override=True)
PATH_TO_FILE = os.path.abspath(__file__)


TOOL_REGISTRY = {
    'tools.calculator': ['multiply', 'add', 'divide'],
    'tools.wikipedia': ['query']
}


def import_function(module_name, function_name):
    """Dynamically imports a function from a module.

    Args:
        module_name: The name of the module (e.g., "my_module").
        function_name: The name of the function to import (e.g., "my_function").

    Returns:
        The imported function, or None if the module or function is not found.
    """
    try:
        module = importlib.import_module(module_name)
        function = getattr(module, function_name)
        return function
    except (ImportError, AttributeError) as e:
        print(f"I'm in cwd: {os.getcwd()}")
        print(f"Available modules: {os.listdir(os.getcwd())}")
        print(
            f"Error: Could not import function '{function_name}' from module '{module_name}'.")
        print(f"Exception: {e}")
        return None


tools = [import_function(module, function) for module,
         functions in TOOL_REGISTRY.items() for function in functions]


llm = ChatOllama(
    model=MODEL,
    temperature=TEMPERATURE,
    # base_url="http://host.docker.internal:11434", # if running in the studio
).bind_tools(tools)


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    claim: str
    # {'name': tool name, 'args': {kwargs}, 'result': str}
    evidence: list[dict]


with open('prompts/research_agent_system_prompt.txt', 'r') as f:
    sys_msg = SystemMessage(content=f.read())


def preprocessing(state: State):
    """
    Preprocesses state before sending to the assistant for tool routing.
    Currently, this just extracts the claim from the state and sets it as a HumanMessage
    following the SystemMessage
    """
    state['messages'] = [sys_msg, HumanMessage(content=state['claim'])]
    return state


def assistant(state: State) -> State:
    response = llm.invoke(state['messages'])
    return {"messages": response}


def postprocessing(state: State) -> State:
    """
    Scan the message history to extract tool calls and results into tuples:
    (tool_name, tool_args, tool_result) for the 'evidence' list in the state
    """

    evidence = []
    for i in range(len(state['messages'])):
        message = state['messages'][i]
        if isinstance(message, AIMessage) and hasattr(message, 'tool_calls'):
            for tool_call in message.tool_calls:
                # Scan later messages for the corresponding ToolMessage
                for j in range(i + 1, len(state['messages'])):
                    next_message = state['messages'][j]
                    if isinstance(next_message, ToolMessage) and next_message.tool_call_id == tool_call['id']:
                        # Found the corresponding ToolMessage
                        evidence.append({
                            'name': tool_call['name'],
                            'args': tool_call['args'],
                            'result': next_message.content})
                        break

    return {'evidence': evidence}
    # return state


# Graph
builder = StateGraph(State)

# Define nodes: these do the work
builder.add_node("preprocessing", preprocessing)
builder.add_node("assistant", assistant)
builder.add_node("tools", ToolNode(tools))
builder.add_node("postprocessing", postprocessing)

# Define edges: these determine how the control flow moves
builder.add_edge(START, "preprocessing")
builder.add_edge("preprocessing", "assistant")
builder.add_conditional_edges(
    source="assistant",
    path=tools_condition,
    path_map={'tools': 'tools', '__end__': 'postprocessing'}
)
builder.add_edge("tools", "assistant")
builder.add_edge("postprocessing", END)

research_agent = builder.compile()
