import requests
from inspect import Signature, Parameter
from functools import wraps
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


def create_tool(
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
    @wraps(api_caller)
    def tool_function(*args, **kwargs):
        bound_args = custom_signature.bind(*args, **kwargs)
        bound_args.apply_defaults()
        return api_caller(**bound_args.arguments)

    # Apply the custom signature and docstring
    tool_function.__signature__ = custom_signature
    tool_function.__doc__ = docstring
    return tool_function


def main():
    # Define the parameter mapping
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

    # Create a tool for querying Pokémon
    get_pokemon = create_tool(
        param_mapping=param_mapping,
        method=method,
        url_template=url_template,
        headers=headers,
        docstring='Get information about a Pokémon from the PokeAPI.',
        target_fields=[['abilities', 0, 'ability', 'name'],
                       ['abilities', 1, 'ability', 'name']],
    )

    # Query for Pikachu with custom parameters
    response = get_pokemon(name='pikachu')
    print(f"Pikachu's abilities: {response}")

    # Query for Bulbasaur with default headers
    response = get_pokemon(name='bulbasaur')
    print(f"Bulbasaur's abilities: {response}")

    # OpenAI version
    param_mapping = {
        'model': 'json',       # Maps to the JSON payload
        'messages': 'json',    # Maps to the JSON payload
        'temperature': 'json',  # Maps to the JSON payload
        'max_tokens': 'json'   # Maps to the JSON payload
    }
    # import os
    # openai_key = os.getenv('OPENAI_API_KEY')
    # assert openai_key, "Please set the OPENAI_API_KEY environment variable."

    # headers = {
    #     # Include your Bearer token here
    #     'Authorization': f'Bearer {openai_key}',
    #     'Content-Type': 'application/json'
    # }
    # get_gpt_completion = create_tool(
    #     method='post',
    #     url_template='https://api.openai.com/v1/chat/completions',
    #     headers=headers,
    #     docstring='Get a completion from the OpenAI GPT API.',
    #     target_fields=[['choices', 0, 'message', 'content']],
    #     param_mapping=param_mapping
    # )

    # response = get_gpt_completion(
    #     model='gpt-4',
    #     messages=[
    #         {"role": "system", "content": "You are a helpful assistant."},
    #         {"role": "user", "content": "What is the capital of France?"}
    #     ],
    #     temperature=0.7,
    #     max_tokens=100
    # )
    # print(f"GPT-4 response: {response}")


if __name__ == "__main__":
    main()
