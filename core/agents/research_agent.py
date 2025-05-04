"""
NOTE: If you want to run this as a standalone script, run
python -m core.agents.research_agent
from project root
"""

from dotenv import load_dotenv
import json
import importlib
import os
from pathlib import Path
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing import Annotated, TypedDict, Callable
from core.agents.tools.tool_registry import create_tool
from core.agents.utils.llm_factory import get_chat_model
from core.agents.utils.common_types import Evidence

DEFAULT_MODEL = "mistral-nemo"  # Default model to use if not specified in .env

# Absolute path to this dir. For handling relative paths like to prompt file
DIR = Path(__file__).parent.resolve()

# Load env variables from core/.env
load_dotenv(DIR.parent / '.env', override=True)

# Import prefix for builtin tools
MODULE_PREFIX = "core.agents.tools.builtins."


def import_builtin(module_name):
    """Dynamically imports a function from a module.

    Args:
        module_name: The name of the module (e.g., "my_module").
        function_name: The name of the function to import (e.g., "my_function").

    Returns:
        The imported function, or None if the module or function is not found.
    """
    import_path = MODULE_PREFIX + module_name
    # Standard interface for builtin tool: each module has a function called tool_function
    function_name = 'tool_function'
    try:
        module = importlib.import_module(import_path)
        function = getattr(module, function_name)
        return function
    except ImportError as e:
        print(
            f"Error: Could not find module '{import_path}'.")
        print(f"cwd: {os.getcwd()}")
        print(f"Exception: {e}")
    except AttributeError as e:
        print(
            f"Error: Function '{function_name}' not found in module '{import_path}'.")
        print(f"Exception: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
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

    tools = []
    for kwargs in tool_kwargs:
        try:
            tool = create_tool(**kwargs)
            tools.append(tool)
        except Exception as e:
            print(f"Error creating tool with kwargs {kwargs}:\n{e}")
    return tools


"""
Static graph components
"""


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    claim: str
    evidence: list[Evidence]


with open(DIR / 'prompts/research_agent_system_prompt.txt', 'r') as f:
    sys_msg = SystemMessage(content=f.read())

with open(DIR / 'prompts/research_agent_filter_evidence_prompt.txt', 'r') as f:
    filter_sys_msg = SystemMessage(content=f.read())


def preprocessing(state: State):
    """
    Preprocesses state before sending to the assistant for tool routing.
    Currently, this just extracts the claim from the state and sets it as a HumanMessage
    following the SystemMessage
    """
    state['messages'] = [sys_msg, HumanMessage(content=state['claim'])]
    return state


def get_assistant_node(llm: BaseChatModel) -> Callable:
    """
    Given reference to LLM, returns an assistant node using that LLM
    """
    def assistant(state: State) -> State:
        response = llm.invoke(state['messages'])
        return {"messages": response}

    return assistant


def gather_evidence(state: State) -> State:
    """
    Scan the message history to extract tool calls and results into tuples:
    (tool_name, tool_args, tool_result) for the 'evidence' list in the state

    #TODO there's possibly a smarter way to do this by matching tool call IDs
    """
    all_evidence = []
    for i in range(len(state['messages'])):
        message = state['messages'][i]
        if isinstance(message, ToolMessage):
            # TODO: pass the list[Evidence] through the tool_message.artifact
            try:
                evidence = json.loads(message.content)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON from tool call: {e}")
                evidence = [message.content]

            all_evidence += evidence

    return {'evidence': all_evidence}


def get_filter_evidence_node(llm: BaseChatModel) -> Callable:
    def filter_evidence(state: State) -> State:
        """
        Iterate over the evidence list, filtering out any evidence that is not relevant to the claim
        """
        # set up a system prompt, SystemMessage
        filtered_evidence = []
        for evidence in state['evidence']:
            prompt = "Claim:\n" + state['claim'] + "\nEvidence:\n" + evidence.content
            messages = [filter_sys_msg, HumanMessage(content=prompt)]
            response = llm.invoke(messages)

            # Load the JSON response
            try:
                response_json = json.loads(response.content)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON from filter response: {e}")
                # Fall back to using the original evidence
                filtered_evidence.append(evidence)
                continue

            # Check if the evidence is relevant
            if response_json['isRelevant']:
                filtered_evidence_item = Evidence(
                    name=evidence.name,
                    args=evidence.args,
                    content=response.content,
                    source=evidence.source
                )
                filtered_evidence.append(filtered_evidence_item)
        state['evidence'] = filtered_evidence
        return state

    return filter_evidence


def create_agent(
        model: str,
        builtin_tools: list[str] = None,
        user_tool_kwargs: list[dict] = None) -> StateGraph:
    """
    Build the research agent graph.
    Args:
        model (str): The model to use for the agent.
        builtin_tools (list[str]): A list of builtin tools to use identified by strings
            The strings are module names, which will be prepending with PACKAGE_PREFIX, 
            values are lists of function names.
            E.g. 'wikipedia' will attempt to import PACKAGE_PREFIX + 'wikipedia'
            (core.agents.tools.builtins.wikipedia)
        user_tool_kwargs (list[dict]): A list of user-defined tools to use.
            each dict should be kwargs needed for tool_registry.create_tool
    Returns:
        StateGraph: The compiled state graph for the research agent.
    """

    # Assemble builtin and user-defined tools
    builtins = [tool for module in builtin_tools if (
        tool := import_builtin(module))]
    user_defined_tools = render_user_defined_tools(
        tool_kwargs=user_tool_kwargs)
    tools = builtins + user_defined_tools

    # Instantiate LLM-based objects for the agent (ChatModel, assistant node)
    if not model:
        model = os.getenv("RESEARCH_AGENT_MODEL", DEFAULT_MODEL)
    llm = get_chat_model(model_name=model).bind_tools(tools)
    assistant = get_assistant_node(llm)
    filter_evidence = get_filter_evidence_node(llm)

    # Build graph
    builder = StateGraph(State)
    builder.add_node("preprocessing", preprocessing)
    builder.add_node("assistant", assistant)
    builder.add_node("tools", ToolNode(tools))
    builder.add_node("gather_evidence", gather_evidence)
    builder.add_node("filter_evidence", filter_evidence)

    builder.add_edge(START, "preprocessing")
    builder.add_edge("preprocessing", "assistant")
    builder.add_conditional_edges(
        source="assistant",
        path=tools_condition,
        path_map={'tools': 'tools', '__end__': 'gather_evidence'},
    )
    builder.add_edge("tools", "assistant")
    builder.add_edge("gather_evidence", filter_evidence)
    builder.add_edge("filter_evidence", END)

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
        builtin_tools=['wikipedia'],
        # user_tool_kwargs=[pokemon_kwargs]
    )
    claim = "Python was created by Guido van Rossum"
    final_state = research_agent.invoke({"claim": claim})
    print(f"Final evidence: {final_state['evidence']}")
    print()


if __name__ == "__main__":
    main()
