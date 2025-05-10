# How to Build API Tools with `create_tool`

This guide explains how to configure `create_tool` to wrap any RESTful API into an agent-callable function.

## Quick Start

```python
from core.agents.tools.tool_registry import create_tool

# Create a weather API tool
weather_tool = create_tool(
    name="get_weather",
    method="GET",
    url_template="https://api.example.com/weather",
    default_params={"api_key": "YOUR_API_KEY"},
    param_mapping={
        "city": {
            "type": "str",
            "for": "params"
        }
    },
    docstring="Get weather for a city"
)
```

## Required Parameters

| Parameter      | Description                                      | Example                                                      |
| -------------- | ------------------------------------------------ | ------------------------------------------------------------ |
| `name`         | Unique tool identifier                           | `"github_issues"`                                            |
| `method`       | HTTP method                                      | `"GET"`, `"POST"`, etc.                                      |
| `url_template` | API endpoint with optional placeholder variables | `"https://api.example.com/users/{user_id}"`                  |
| `docstring`    | Instructions shown to the LLM                    | `"Search for GitHub issues. Args: query (str): Search term"` |

## Optional Parameters

| Parameter        | Description                     | Default |
| ---------------- | ------------------------------- | ------- |
| `headers`        | HTTP headers                    | `None`  |
| `default_params` | Query parameters                | `None`  |
| `data`           | Form data                       | `None`  |
| `json`           | JSON body                       | `None`  |
| `target_fields`  | Fields to extract from response | `None`  |
| `param_mapping`  | Function parameter mapping      | `{}`    |

## Parameter Mapping Structure

The `param_mapping` dictionary is the key to making your API tool dynamic:

```python
param_mapping = {
    "parameter_name": {  # Name the LLM will use
        "type": "str",   # Data type (str, int, float, bool, list, dict)
        "for": "params"  # Where to use it (url_params, params, headers, data, json)
    }
}
```

### Mapping Types

- `"url_params"`: Replace placeholders in the URL template
- `"params"`: Add to query parameters (?key=value)
- `"headers"`: Add to HTTP headers
- `"data"`: Add to form data
- `"json"`: Add to JSON body

## Response Handling with `target_fields`

To extract specific fields from complex API responses:

```python
target_fields = [
    ["results", 0, "name"],   # Extracts response["results"][0]["name"]
    ["metadata", "count"]     # Extracts response["metadata"]["count"]
]
```

## Complete Example

```python
github_issues_tool = create_tool(
    name="github_issues",
    method="GET",
    url_template="https://api.github.com/repos/{owner}/{repo}/issues",
    headers={
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {github_token}"
    },
    param_mapping={
        "owner": {
            "type": "str",
            "for": "url_params"  # Replaces {owner} in URL
        },
        "repo": {
            "type": "str",
            "for": "url_params"  # Replaces {repo} in URL
        },
        "state": {
            "type": "str",
            "for": "params"      # Adds ?state=value to URL
        }
    },
    target_fields=[
        ["number"],              # Issue number
        ["title"],               # Issue title
        ["state"]                # Issue state
    ],
    docstring="""Fetch GitHub issues for a repository.
    Args:
        owner (str): Repository owner
        repo (str): Repository name
        state (str, optional): Issue state (open, closed, all)
    Returns:
        List of issues with number, title and state
    """
)
```

## Tool Interface Explanation

NewsAgent builtin tools and custom tools implement essentially the same interface:

- Can take any number of parameters
- Returns a tuple `(json.dumps(list[Evidence]), list[Evidence])`

Both builtin and custom tools get wrapped in LangChain's `StructuredTool` decorator with `response_format="content_and_artifact"`. So conceptually, the tool function will only return the serialized evidence list and the `list[Evidence]` appears on the call's ToolMessage `.artifact` attribute (see LangChain [https://python.langchain.com/docs/how_to/tool_artifacts/](https://python.langchain.com/docs/how_to/tool_artifacts/))

Given a ToolMessage should have content on its `content` attribute, we serialize the tool call's assembled evidence to accurately return it. However, since by the end of a tool call our desired evidence presumably already resides in the desired `list[Evidence]` object, the Research Agent fist checks the ToolMessage's artifact for a valid `list[Evidence]` object. Failing that, it attempts to parse the `content` attribute. If that fails as well, it creates an `Evidence` list with a single item, including the raw string content from the ToolMessage.

Builtin tools should exist each in their own file and be called `tool_function`; its unique name gets assigned by the `tool` decorator. Custom tools receive their name by user-supplied kwargs.
