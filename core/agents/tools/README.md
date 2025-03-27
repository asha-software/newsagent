# Tool Registry

A flexible Python utility for creating API client functions with minimal boilerplate. The Tool Registry provides a generic way to create callable tools that can bind to LLMs and interact with REST APIs.

To use `create_tool` the user passes in the typical fields required to form an HTTP request to an API endpoint, including the method, url, headers, and any parameters required.

The user can make most parts of the request object parameters of the tool function created. For instance, certain header fields or parts of the url can be set as parameters themselves to be specified when invoking the tool.

Example:

```python
    url_template = 'https://pokeapi.co/api/v2/pokemon/{name}'
    headers = {'Accept': 'application/json'}

    # This tells the tool function that it takes one parameter, `name`, used in the url template
    param_mapping = {
        'name': 'url_params',  # Maps to URL placeholders
    }

    # Here we specify which fields we want from the response object:
    """
    [
        response['abilities'][0]['ability']['name'],
        response['abilities][1]['ability']['url]
    ]
    """
    target_fields = [['abilities', 0, 'ability', 'name'],
                       ['abilities', 1, 'ability', 'url']]

    # Create a tool for querying Pokémon
    get_pokemon = create_tool(
        method='GET', url_template=url_template, headers=headers,
        docstring='Get information about a Pokémon from the PokeAPI.\nArgs:\n  name: name of the pokemon you want',
        target_fields=target_fields,
        param_mapping=param_mapping
    )
```

## `create_tool`

- `method: str`: the HTTP verb expected by the endpoing (`GET`, `POST`, etc.)
- `url_template: str`: a string or string template which can be configured by values in `param_mapping['url_params']`
- `headers: str`:
- `default_params: dict`: 'always-on' parameters, although these can be overridden by values in `param_mapping` provided by the LLM at runtime.
- `data: str`: any text you always want sent in the data field
- `json: dict`: any dict data you always want sent in the json field
- `target_fields: list[list[str|int]]`: A 2d list where each inner list describes one field that should be retrieved from the response object. Use strings for keys or properties, ints for array indices
- `param_mapping: dict[str, Literal['url_params', 'params', 'headers', 'json', 'data']]`: This dictionary takes the keys and sets them as parameters in the returned tool function. The values for each key determine where the argument will be applied: in the url, params, headers, etc.
