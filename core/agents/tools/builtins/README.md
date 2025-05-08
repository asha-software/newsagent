# README for Newsagent Tools

## Builtin Tools

Builtin tools follow a common interface:

- One file per tool
- Each file defines a `tool_function` which implements the tool using Google-style docstrings
- The `tool_function` can have any parameters but it returns a list (one or more) of `Evidence` (see `core.agents.utils.common_types`)
- The `tool_function` receives the `langchain_core.tools.tool` decorator with `parse_docstring=True` to generate input validation model

## Creating Custom Tools

The Tool Registry's `create_tool` function allows you to wrap any RESTful API into an agent-callable function:

```python
from core.agents.tools.tool_registry import create_tool

weather_tool = create_tool(
    name="get_weather",
    method="GET",
    url_template="https://api.example.com/weather/{city}",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
    param_mapping={
        "city": {
            "type": "str",
            "for": "url_params"
        },
        "units": {
            "type": "str",
            "for": "params"
        }
    },
    docstring="Get weather for a city. Args: city (str): City name, units (str, optional): Temperature units"
)
```

### Parameter Mapping

The `param_mapping` dictionary configures how function parameters are mapped to HTTP requests:

```python
param_mapping = {
    "parameter_name": {
        "type": "str",   # Data type (str, int, float, bool, list, dict)
        "for": "params"  # Where to use it (url_params, params, headers, data, json)
    }
}
```

### Response Handling

Use `target_fields` to extract specific data from API responses, so as not to overload the reasoning agent:

```python
target_fields = [
    ["weather", 0, "description"],  # Extracts weather[0].description
    ["main", "temp"]                # Extracts main.temp
]
```