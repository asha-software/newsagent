from typing import Annotated, TypedDict
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
import requests
from inspect import Signature, Parameter
# from functools import wraps

from langchain.tools import StructuredTool, tool
from typing import Literal

TYPE_MAPPING = {
    "int": int,
    "str": str,
    "float": float,
    "bool": bool,
    "array": list,
    "object": dict,
    "None": type(None)  # For NoneType
}


def extract_fields(obj: dict, listpath_to_field: list):
    """
    Recursively extracts properties/indices from a list.
    """
    # Base case:
    if not listpath_to_field:
        return obj

    target = listpath_to_field.pop(0)
    # Case: next field is an index
    if isinstance(target, int):
        return extract_fields(obj[target], listpath_to_field)

    # Case: next field is a property
    if hasattr(obj, target):
        print(f"{target} is a property of obj")
        return extract_fields(getattr(obj, target), listpath_to_field)

    # Case: next field is an index or string key
    return extract_fields(obj[target], listpath_to_field)


def create_tool(
    name: str,
    param_mapping: dict[str, dict[str, str | Literal['url_params', 'params', 'headers', 'data', 'json']]],
    # NOTE: Do we need to support the DELETE or PATCH verbs?
    method: Literal['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
    url_template: str,
    headers: dict[str, str] = None,
    default_params: dict[str, str] = None,
    data: dict[str, str] = None,
    json: dict[str, str] = None,
    docstring: str = "",
    target_fields: list[list[str | int]] = None,
):
    """
    This function takes in various parameters to configure an API request, leaving some values as variables the user can specify later.
    It returns a function with a user-specified signature that can be bound to an LLM as a tool, allowing users to add their own API services
    to NewsAgent without having to modify the core code or execute arbitrary code on our servers.

    Args:
        method (str): The HTTP method to use (e.g., 'GET', 'POST')
        url_template (str): A URL template with placeholders for parameters
        headers (dict, optional): Default headers to include in the request. Defaults to None.
        default_params (dict, optional): Default parameters to include in the request. Defaults to None.
        data (dict, optional): Default data to include in the request. Defaults to None.
        json (dict, optional): Default JSON payload to include in the request. Defaults to None.
        docstring (str): The docstring for the generated function. These are the instructions passed to the LLM 
            the return function's usage
        target_fields (list, optional): A list of listpaths to extract from the response JSON. Defaults to None.
        param_mapping (dict): A mapping of function arguments to request components. Defaults to None.
            {
                'param_name': {
                    'type': 'str',
                    'for': 'url_params', 'params', 'headers', 'data', 'json'
                    },
            }
    """

    def api_caller(**kwargs):
        # Initialize request components
        url_params = {}
        req_headers = headers.copy() if headers else {}
        req_params = default_params.copy() if default_params else {}
        req_data = data.copy() if data else {}
        req_json = json.copy() if json else {}

        # Map user-provided arguments to the appropriate request components
        for param_name, param_value in kwargs.items():
            if param_name in param_mapping:
                param_info = param_mapping[param_name]
                param_type = TYPE_MAPPING[param_info['type']]  # Validate type
                if not isinstance(param_value, param_type):
                    raise TypeError(
                        f"Parameter '{param_name}' must be of type {param_info['type']}.")

                # Map the parameter to the correct request component
                if param_info['for'] == 'url_params':
                    url_params[param_name] = param_value
                elif param_info['for'] == 'headers':
                    req_headers[param_name] = param_value
                elif param_info['for'] == 'params':
                    req_params[param_name] = param_value
                elif param_info['for'] == 'data':
                    req_data[param_name] = param_value
                elif param_info['for'] == 'json':
                    req_json[param_name] = param_value

        # Format the URL with URL parameters
        url = url_template.format(**url_params)

        # Make the API request
        response = requests.request(
            method=method,
            url=url,
            headers=req_headers,
            params=req_params,
            data=req_data,
            json=req_json
        )
        try:
            response_json = response.json()
        except ValueError:
            print(
                f"Error: Could not parse response as JSON. Response text: {response.text}")
            return response.text

        if target_fields:
            return_fields = []
            for listpath in target_fields:
                # Make a copy of the listpath to avoid mutating the original
                return_fields.append(extract_fields(
                    response_json, listpath[:]))
            return return_fields
        return response

    # Dynamically create the function signature
    parameters = [
        Parameter(
            name=param_name,
            kind=Parameter.POSITIONAL_OR_KEYWORD,
            annotation=TYPE_MAPPING[param_info['type']]
        )
        for param_name, param_info in param_mapping.items()
    ]
    custom_signature = Signature(parameters=parameters)

    # Define the tool function
    def tool_function(*args, **kwargs):
        bound_args = custom_signature.bind(*args, **kwargs)
        bound_args.apply_defaults()
        return api_caller(**bound_args.arguments)

    # Create arguments schema dictionary for LangChain
    args_schema = {
        param_name: {  # Use parameter name as key
            "description": f"{param_name} parameter",
            "type": param_info['type']
        }
        for param_name, param_info in param_mapping.items()
    }

    return StructuredTool.from_function(
        func=tool_function,
        name=name,
        description=docstring,
        args_schema=args_schema
    )


def main():
    # Define the parameter mapping
    name = 'PokemonAPI'
    param_mapping = {
        'name': {
            'type': 'str',
            'for': 'url_params'
        }
    }
    method = 'GET'
    # Use a URL template with a placeholder for the Pokémon name
    url_template = 'https://pokeapi.co/api/v2/pokemon/{name}'
    headers = {'Accept': 'application/json'}
    docstring = '''Get information about a Pokémon from the PokeAPI.
    Args:
        name (str): The name of the Pokémon to query, ALWAYS LOWERCASED.
    Returns:
        list: A list containing the Pokémon's abilities.
    '''
    kwargs = {
        'name': name,
        'param_mapping': param_mapping,
        'method': method,
        'url_template': url_template,
        'headers': headers,
        'docstring': docstring,
        'target_fields': [['abilities', 0, 'ability', 'name'],
                          ['abilities', 1, 'ability', 'name']],
    }
    # Create a tool for querying Pokémon
    get_pokemon = create_tool(
        name=name,
        param_mapping=param_mapping,
        method=method,
        url_template=url_template,
        headers=headers,
        docstring=docstring,
        target_fields=[['abilities', 0, 'ability', 'name'],
                       ['abilities', 1, 'ability', 'name']],
    )

    # fmt: off
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, SystemMessage
    from langchain_ollama import ChatOllama
    from langgraph.graph import StateGraph, START, END
    from langgraph.graph.message import add_messages
    from langgraph.prebuilt import ToolNode, tools_condition
    from typing import Annotated, TypedDict
    # fmt: on

    def create_agent(tools: list, system_prompt: str) -> StateGraph:
        """
        Build a simple agent that routes to a ToolNode when the LLM requests it.
        """
        # Simple ChatOllama config (binds the provided tools).
        llm = ChatOllama(model="mistral-nemo", temperature=0).bind_tools(tools)

        class State(TypedDict):
            messages: Annotated[list, add_messages]

        sys_msg = SystemMessage(content=system_prompt)

        def preprocessing(state: State) -> State:
            # Put the user’s question into the messages.
            content = state['messages'][-1].content if state['messages'] else "No user input"
            state['messages'] = [sys_msg, HumanMessage(content=content)]
            return state

        def assistant(state: State) -> State:
            # Let the LLM respond, possibly with a tool call
            response = llm.invoke(state['messages'])
            return {"messages": response}

        # Build a graph with a Tools node
        sg = StateGraph(State)
        sg.add_node("preprocessing", preprocessing)
        sg.add_node("assistant", assistant)
        # Invokes the tools automatically
        sg.add_node("tools", ToolNode(tools))

        sg.add_edge(START, "preprocessing")
        sg.add_edge("preprocessing", "assistant")
        sg.add_conditional_edges(
            source="assistant",
            path=tools_condition,   # <— checks if AI’s message has tool_calls
            path_map={'tools': 'tools', '__end__': END}
        )
        sg.add_edge("tools", "assistant")

        return sg.compile()

    agent = create_agent(
        tools=[get_pokemon],
        system_prompt="You are a helpful assistant. You can query the PokeAPI to get information about Pokémon."
    )
    final_state = agent.invoke(
        {"messages": [HumanMessage(content="What are the abilities of Pikachu?")]})
    for message in final_state["messages"]:
        message.pretty_print()


if __name__ == "__main__":
    main()
