import requests
from inspect import Signature, Parameter
from functools import wraps
from typing import Literal


def create_tool(
    param_mapping: dict[str, Literal['url_params', 'params', 'headers', 'data', 'json']],
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
    """

    def api_caller(**kwargs):
        # Extract URL parameters from kwargs and format the URL
        url = url_template.format(**kwargs.pop('url_params', {}))

        # Start with default params, and update if 'params' is provided via kwargs
        params = default_params.copy() if default_params else {}
        if 'params' in kwargs:
            params.update(kwargs.pop('params'))

        # If headers or other arguments are passed via kwargs, you can also handle them similarly
        req_headers = headers.copy() if headers else {}
        if 'headers' in kwargs:
            req_headers.update(kwargs.pop('headers'))

        # Other kwargs (like data or json) can override the defaults provided to create_api_caller
        req_data = kwargs.pop('data', data)
        req_json = kwargs.pop('json', json)

        # Any other remaining kwargs can be passed directly to requests.request
        response = requests.request(
            method=method,
            url=url,
            headers=req_headers,
            params=params,
            data=req_data,
            json=req_json,
            **kwargs  # Pass any additional keyword arguments to requests.request
        )
        return response

    def extract_fields(obj, listpath_to_field):
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

    def tool(**kwargs):
        """Placeholder"""
        response = api_caller(**kwargs)
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

    # Dynamically create the function signature based on param_mapping
    if param_mapping:
        parameters = []
        for param_name, param_type in param_mapping.items():
            parameters.append(
                Parameter(param_name, Parameter.POSITIONAL_OR_KEYWORD, annotation=param_type))
        custom_signature = Signature(parameters)

        @wraps(tool)
        def wrapped_tool(*args, **kwargs):
            bound_args = custom_signature.bind(*args, **kwargs)
            bound_args.apply_defaults()

            # Map arguments to the appropriate request components
            mapped_kwargs = {}
            for param_name, value in bound_args.arguments.items():
                if param_name in param_mapping:
                    mapped_kwargs.setdefault(param_mapping[param_name], {})[
                        param_name] = value
                else:
                    mapped_kwargs[param_name] = value

            return tool(**mapped_kwargs)

        # Apply the custom signature
        wrapped_tool.__signature__ = custom_signature
        wrapped_tool.__doc__ = docstring
        return wrapped_tool

    tool.__doc__ = docstring
    return tool


def main():
    # Use a URL template with a placeholder for the Pokémon name
    url_template = 'https://pokeapi.co/api/v2/pokemon/{name}'
    headers = {'Accept': 'application/json'}

    # Define the parameter mapping
    param_mapping = {
        'name': 'url_params',  # Maps to URL placeholders
    }

    # Create a tool for querying Pokémon
    get_pokemon = create_tool(
        'GET', url_template, headers,
        docstring='Get information about a Pokémon from the PokeAPI.',
        target_fields=[['abilities', 0, 'ability', 'name'],
                       ['abilities', 1, 'ability', 'name']],
        param_mapping=param_mapping
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
    import os
    openai_key = os.getenv('OPENAI_API_KEY')
    assert openai_key, "Please set the OPENAI_API_KEY environment variable."

    headers = {
        # Include your Bearer token here
        'Authorization': f'Bearer {openai_key}',
        'Content-Type': 'application/json'
    }
    get_gpt_completion = create_tool(
        method='post',
        url_template='https://api.openai.com/v1/chat/completions',
        headers=headers,
        docstring='Get a completion from the OpenAI GPT API.',
        target_fields=[['choices', 0, 'message', 'content']],
        param_mapping=param_mapping
    )

    response = get_gpt_completion(
        model='gpt-4',
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is the capital of France?"}
        ],
        temperature=0.7,
        max_tokens=100
    )
    print(f"GPT-4 response: {response}")


if __name__ == "__main__":
    main()
