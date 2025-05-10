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
from core.agents.utils.common_types import Evidence, EvidenceListModel

DEFAULT_MODEL = "mistral-nemo"  # Default model to use if not specified in .env

# Absolute path to this dir. For handling relative paths like to prompt file
DIR = Path(__file__).parent.resolve()

# Load env variables from core/.env
load_dotenv(DIR.parent / '.env', override=True)

# Import prefix for builtin tools
MODULE_PREFIX = "core.agents.tools.builtins."
EVIDENCE_REQUIRED_KEYS = Evidence.__required_keys__


def import_builtin(module_name):
    """Dynamically imports a function from a module.

    Args:
        module_name: The name of the module (e.g., "my_module").
        function_name: The name of the function to import (e.g., "my_function").

    Returns:
        The imported function, or None if the module or function is not found.
    """
    # TODO: this is just a hacky patch; resolve this for real
    module_name = "wikipedia_tool" if module_name == "wikipedia" else module_name

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

# FILTER_OUTPUT_FORMAT = {
#     "type": "array",
#     "items": {
#         "type": "string"
#     }
# }


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
    Scan the message history to extract tool calls and the evidence they produced.
    1. Iterates over all messages in the state, looking for ToolMessages
    2. Checks each ToolMessage if it has an artifact that's list[Evidence]
    3. If not, attempts to parse message.content to list[Evidence] 
    4. If that fails, uses string content of the message as evidence

    #TODO there's possibly a smarter way to do this by matching tool call IDs
    """
    all_evidence = []
    for i in range(len(state['messages'])):
        message = state['messages'][i]
        if not isinstance(message, ToolMessage):
            continue

        # Try to get list[Evidence] from artifact
        try:
            validated = EvidenceListModel.model_validate(message.artifact)
            evidence_list = validated.root
        except Exception as e:
            print(f"Error: artifact in tool message didn't validate as list[Evidence]. Attempting to load from message.content. Error message: {e}")

            # If artifact not valid list[Evidence], try to get it from message.content
            try:
                validated = EvidenceListModel.model_validate_json(message.content)
                evidence_list = validated.root
            except Exception as e:
                # If message.content not valid JSON, just use its string content as is
                print(f"Error: message.content didn't parse as json to a valid list[Evidence]. Attempting to load from message.content. Error message: {e}")
                salvaged_evidence = Evidence(
                    name=message.name,
                    # TODO: get this from the corresponding AI Message's tool call
                    args={'info': 'see trace'},
                    content=message.content,
                    source=message.name)
                evidence_list = [salvaged_evidence]

        all_evidence += evidence_list

    # Confirm that all evidence is list[Evidence]
    try:
        evidence_list = EvidenceListModel.model_validate(all_evidence)
    except Exception as e:
        print(f"Error: evidence list didn't validate as list[Evidence]. Error message: {e}")
        # If not, just use the string content of the evidence
        evidence_list = [
            Evidence(
                name="unknown",
                args={},
                content=str(e),
                source="unknown"
            )
        ]

    return {'evidence': all_evidence}


# def get_filter_evidence_node(llm: BaseChatModel) -> Callable:
#     def filter_evidence(state: State) -> State:
#         """
#         Iterate over the evidence list, filtering out any evidence that is not relevant to the claim
#         """
#         filtered_evidence = []
#         print(f"I'm a filter node and I don't do anything yet")

#         for evidence in state['evidence']:
#             prompt = "Claim:\n" + state['claim'] + "\Text to read:\n" + str(evidence['content'])
#             messages = [filter_sys_msg, HumanMessage(content=prompt)]
#             response = llm.invoke(messages)
#             print(f"Response: {response}")

#         return {}

#     return filter_evidence


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

    # Build graph
    builder = StateGraph(State)
    builder.add_node("preprocessing", preprocessing)
    builder.add_node("assistant", assistant)
    builder.add_node("tools", ToolNode(tools))
    builder.add_node("gather_evidence", gather_evidence)

    builder.add_edge(START, "preprocessing")
    builder.add_edge("preprocessing", "assistant")
    builder.add_conditional_edges(
        source="assistant",
        path=tools_condition,
        path_map={'tools': 'tools', '__end__': 'gather_evidence'},
    )
    builder.add_edge("tools", "assistant")
    builder.add_edge("gather_evidence", END)

    # Filter evidence: unfinished
    # TODO: factor out the filtering LLM's model name; it need not be the same as the assistant's
    # filter_llm = llm = get_chat_model(
    #     model_name=os.getenv("RESEARCH_AGENT_MODEL", DEFAULT_MODEL),
    #     format_output=FILTER_OUTPUT_FORMAT,
    # )
    # filter_evidence = get_filter_evidence_node(filter_llm)
    # builder.add_node("filter_evidence", filter_evidence)
    # builder.add_edge("gather_evidence", "filter_evidence")
    # builder.add_edge("filter_evidence", END)

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
    # print(f"Final evidence: {final_state['evidence']}")
    print()


if __name__ == "__main__":
    main()
