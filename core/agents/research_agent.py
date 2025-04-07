"""
NOTE: If you want to run this as a standalone script, run
python -m core.agents.research_agent
from project root
"""

from dotenv import load_dotenv
import importlib
import os
from pathlib import Path

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing import Annotated, TypedDict, Callable
from core.agents.utils.llm_factory import get_chat_model
from core.agents.utils.common_types import Evidence

# Absolute path to this dir. For relative paths like prompts
DIR = Path(__file__).parent.resolve()

# Absolute path to repo root. This will be used to import builtin tools and Evidence from common_types
ROOT_DIR = DIR.parent.parent

# Path prefix for builtin tools
PACKAGE_PREFIX = "core.agents.tools.builtins."

load_dotenv(DIR.parent / '.env', override=True)
assert "RESEARCH_AGENT_MODEL" in os.environ, "Please set the RESEARCH_AGENT_MODEL environment variable"
PATH_TO_FILE = os.path.abspath(__file__)


def import_builtin(module_name):
    """Dynamically imports a function from a module.

    Args:
        module_name: The name of the module (e.g., "my_module").
        function_name: The name of the function to import (e.g., "my_function").

    Returns:
        The imported function, or None if the module or function is not found.
    """
    import_path = PACKAGE_PREFIX + module_name
    # Standard interface for builtin tool: each module has a function called tool_function
    function_name = 'tool_function'
    try:
        module = importlib.import_module(import_path)
        function = getattr(module, function_name)
        return function
    except (ImportError, AttributeError) as e:
        print(
            f"Error: Could not find module '{import_path}'.")
        print(f"cwd: {os.getcwd()}")
        print(f"Exception: {e}")
    except AttributeError as e:
        print(
            f"Error: Function '{function_name}' not found in module '{import_path}'.")
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

    from core.agents.tools.tool_registry import create_tool

    tools = []
    for kwargs in tool_kwargs:
        try:
            tool = create_tool(**kwargs)
            tools.append(tool)
        except Exception as e:
            print(f"Error creating tool with kwargs {kwargs}:\n{e}")
    return tools


def create_agent(
        model: str,
        builtin_tools: dict[str, str] = None,
        user_tool_kwargs: list[dict] = None) -> StateGraph:
    """
    Build the research agent graph.
    Args:
        model (str): The model to use for the agent.
        builtin_tools (dict[str, str]): A dictionary of builtin tools to use.
            Keys are package names, which will be prepending with PACKAGE_PREFIX, 
            values are lists of function names.
            E.g. {'wikipedia': ['query']} will attempt to import PACKAGE_PREFIX + 'wikipedia' and
            use the 'query' function from that module. (core.agents.tools.builtins.wikipedia.query)
        user_tools (list[dict]): A list of user-defined tools to use.
            each dict should be kwargs needed for tool_registry.create_tool
    Returns:
        StateGraph: The compiled state graph for the research agent.
    """

    # Get builtin tools, filter out None values
    builtins = [tool for module in builtin_tools if (
        tool := import_builtin(module))]

    # Handle user-defined tools
    user_defined_tools = render_user_defined_tools(
        tool_kwargs=user_tool_kwargs)

    tools = builtins + user_defined_tools
    if not model:
        model = os.getenv("RESEARCH_AGENT_MODEL")

    llm = get_chat_model(model_name=model).bind_tools(tools)

    class State(TypedDict):
        messages: Annotated[list[BaseMessage], add_messages]
        claim: str
        evidence: list[Evidence]

    with open(DIR / 'prompts/research_agent_system_prompt.txt', 'r') as f:
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
                            evidence_item = Evidence(
                                name=tool_call['name'], args=tool_call['args'], result=next_message.content)
                            evidence.append(evidence_item)
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
    builtin_tools_wanted = ['wikipedia', 'web_search']

    pokemon_kwargs = {
        'name': 'pokeapi',
        'method': 'GET',
        'headers': {'Accept': 'application/json'},
        'url_template': 'https://pokeapi.co/api/v2/pokemon/{name}',
        'docstring': '''Get information about a Pokémon from the PokeAPI.
    Args:
        name (str): The name of the Pokémon to query, ALWAYS LOWERCASED.
    Returns:
        list: A list containing the Pokémon's abilities.
    ''',
        'target_fields': [['abilities', 0, 'ability', 'name'],
                          ['abilities', 1, 'ability', 'name']],
        'param_mapping': {
            'name': {
                'type': 'str',
                'for': 'url_params'
            }
        },
    }
    research_agent = create_agent(
        model='mistral-nemo',
        builtin_tools=builtin_tools_wanted,
        user_tool_kwargs=[pokemon_kwargs]
    )
    # claim = "Python was created by Guido van Rossum"
    # final_state = research_agent.invoke({"claim": claim})
    # print(f"Final evidence: {final_state['evidence']}")
    # print()


if __name__ == "__main__":
    main()
