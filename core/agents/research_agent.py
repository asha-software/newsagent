from dotenv import load_dotenv
import importlib
import os
from pathlib import Path
import sys

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing import Annotated, TypedDict, Callable

# Absolute path to this dir. For relative paths like prompts
BASE_DIR = Path(__file__).parent.resolve()

# Absolute path to repo root. This will be used to import builtin tools
ROOT_DIR = BASE_DIR.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Path prefix for builtin tools
PACKAGE_PREFIX = "core.agents.tools"

load_dotenv(ROOT_DIR / 'core/.env', override=True)
PATH_TO_FILE = os.path.abspath(__file__)


TOOL_REGISTRY = {
    'calculator': ['multiply', 'add', 'divide'],
    'wikipedia': ['query']
}


def import_builtin(module_name, function_name):
    """Dynamically imports a function from a module.

    Args:
        module_name: The name of the module (e.g., "my_module").
        function_name: The name of the function to import (e.g., "my_function").

    Returns:
        The imported function, or None if the module or function is not found.
    """
    try:
        module = importlib.import_module(
            f"{PACKAGE_PREFIX}.{module_name}")
        function = getattr(module, function_name)
        return function
    except (ImportError, AttributeError) as e:
        print(
            f"Error: Could not import function '{function_name}' from module '{module_name}'.")
        print(f"cwd: {os.getcwd()}")
        print(f"Available modules: {os.listdir(os.getcwd())}")
        print(f"Exception: {e}")
        return None


def render_user_defined_tools(tool_kwargs: list[dict]) -> list[Callable]:
    """
    Takes a list of kwargs for user-defined tools and returns a list of tool instances.
    Args:
        tool_kwargs (list[dict]): A list of dictionaries, each dict comprising kwargs needed
            for tool_registry.create_tool
    Returns:
        list[Callable]: A list of tool instances created from the provided kwargs, to bind to LLM
    """
    if not tool_kwargs:
        return []

    create_tool = getattr(importlib.import_module(
        f"{PACKAGE_PREFIX}.tool_registry"), "create_tool")

    return [
        create_tool(**kwargs) for kwargs in tool_kwargs]


def create_agent(
        model: str = 'mistral-nemo',
        builtin_tools: dict[str, str] = None,
        user_tool_kwargs: list[dict] = None) -> StateGraph:
    """
    Build the research agent graph.
    Args:
        model (str): The model to use for the agent.
        builtin_tools (dict[str, str]): A dictionary of builtin tools to use.
            Keys are module names, values are lists of function names.
        user_tools (list[dict]): A list of user-defined tools to use.
            each dict should be kwargs needed for tool_registry.create_tool
    Returns:
        StateGraph: The compiled state graph for the research agent.
    """

    # Handle builtin tools
    builtins = [import_builtin(module, function) for module,
                functions in builtin_tools.items() for function in functions]
    
    # Filter out None values (failed imports)
    builtins = [tool for tool in builtins if tool is not None]

    # Handle user-defined tools
    user_defined_tools = render_user_defined_tools(
        tool_kwargs=user_tool_kwargs)

    tools = builtins + user_defined_tools

    # TODO: switch on model type to allow ChatOpenAI, ChatAnthropic, etc.
    llm = ChatOllama(
        model=model,
        temperature=0,
        base_url="http://host.docker.internal:11434", # if running in the studio
    ).bind_tools(tools)  # Use the filtered tools list

    class State(TypedDict):
        messages: Annotated[list[BaseMessage], add_messages]
        claim: str
        evidence: list[dict]

    with open(BASE_DIR / 'prompts/research_agent_system_prompt.txt', 'r') as f:
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

    agent = builder.compile()
    return agent


def main():
    builtin_tools_wanted = {
        'calculator': ['multiply', 'add'],
        'wikipedia': ['query']
    }

    user_kwargs = {
        'method': 'GET',
        'url_template': 'https://pokeapi.co/api/v2/pokemon/{name}',
        'docstring': 'Get information about a Pokémon from the PokeAPI.',
        'headers': {'Accept': 'application/json'},
        'target_fields': [['abilities', 0, 'ability', 'name'],
                          ['abilities', 1, 'ability', 'name']],
        'param_mapping': {
            'name': 'url_params',  # Maps to URL placeholders
        },
    }
    research_agent = create_agent(
        model='mistral-nemo',
        builtin_tools=builtin_tools_wanted,
        user_tool_kwargs=[]
    )
    # claim = "Python was created by Guido van Rossum"
    # final_state = research_agent.invoke({"claim": claim})
    # print(f"Final evidence: {final_state['evidence']}")
    # print()


if __name__ == "__main__":
    main()
