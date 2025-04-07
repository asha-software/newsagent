# API Usage

This document explains how to use the NewsAgent API.

## Obtaining an API Key

There are several ways to obtain an API key:

1. **Automatic Generation**: API keys are automatically generated when you use the web interface to search for news claims. The system will create an API key for your account if you don't already have one.

2. **User-Created Keys**: You can create your own API keys through the "API Keys" page. This allows you to create multiple keys for different applications or services.

3. **Admin Creation**: Administrators can create API keys for users through the Django admin interface.

## Using an API Key

To use an API key, include it in the `X-API-Key` header of your requests:

```
X-API-Key: your-api-key
```

Example using curl:

```bash
curl -X POST \
  http://localhost:8001/query \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: your-api-key' \
  -d '{"body": "Your query text here"}'
```

When you use an API key, the system tracks its usage by updating the `last_used_at` timestamp in the database. This provides an audit trail of API key usage and helps identify inactive keys.

## Rate Limiting

To ensure fair usage of the API, rate limiting is enforced on the `/query` endpoint:

- **Limit**: 10 requests per minute per API key
- **Reset**: The rate limit window resets 60 seconds after your first request in the current window
- **Headers**: The API includes rate limit information in the response headers:
  - `X-Rate-Limit-Limit`: The maximum number of requests allowed per minute
  - `X-Rate-Limit-Remaining`: The number of requests remaining in the current window

If you exceed the rate limit, the API will return a `429 Too Many Requests` response with the following body:

```json
{
  "detail": "Rate limit exceeded. Try again in X seconds.",
  "rate_limit": {
    "limit": 2,
    "remaining": 0,
    "reset_after_seconds": X
  }
}
```

Where `X` is the number of seconds until the rate limit resets.

Note: This rate limit is currently set to 2 requests per minute for testing purposes and may be adjusted in the future.

## Managing API Keys

### Web Interface

You can manage your API keys through the web interface:

1. **Viewing Keys**: Navigate to the "API Keys" page to see all your API keys.
2. **Creating Keys**: Click the "Create New API Key" button to generate a new API key.
3. **Deleting Keys**: Click the "Delete" button next to an API key to remove it.

**Note**: There is a limit of 3 API keys per user account. If you need to create a new API key but have reached the limit, you must delete an existing key first.

### API Endpoints

You can also manage your API keys programmatically:

#### Creating API Keys

To create a new API key:

```
POST http://localhost:8001/api-keys
```

Request body:

```json
{
  "name": "My New API Key"
}
```

Example using curl:

```bash
curl -X POST \
  http://localhost:8001/api-keys \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: your-existing-api-key' \
  -d '{"name": "My New API Key"}'
```

Response:

```json
{
  "id": 2,
  "name": "My New API Key",
  "key": "generated-api-key",
  "created_at": "2023-01-03T00:00:00.000Z",
  "last_used_at": null,
  "is_active": true
}
```

Error response (when limit is reached):

```json
{
  "detail": "You can only have a maximum of 3 API keys per account."
}
```

Note: This endpoint requires authentication with an existing API key. You must include your existing API key in the `X-API-Key` header. There is a limit of 3 API keys per user account.

#### Listing API Keys

To list all your API keys:

```
GET http://localhost:8001/api-keys
```

Example using curl:

```bash
curl -X GET \
  http://localhost:8001/api-keys \
  -H 'X-API-Key: your-existing-api-key'
```

Response:

```json
[
  {
    "id": 1,
    "name": "My API Key",
    "key": "your-api-key",
    "created_at": "2023-01-01T00:00:00.000Z",
    "last_used_at": "2023-01-02T00:00:00.000Z",
    "is_active": true
  }
]
```

Note: This endpoint requires authentication with an existing API key.

#### Deleting an API Key

To delete an API key:

```
DELETE http://localhost:8001/api-keys/{api_key_id}
```

Example using curl:

```bash
curl -X DELETE \
  http://localhost:8001/api-keys/<id> \
  -H 'X-API-Key: your-existing-api-key'
```

Response:

```json
{
  "message": "API key deleted successfully"
}
```

Note: This endpoint requires authentication with an existing API key. Replace `{api_key_id}` with the ID of the API key you want to delete.

## Available API Endpoints

### Health Check

Check if the API is up and running:

```
GET /health
```

Example using curl:

```bash
curl http://localhost:8001/health
```

Response:

```json
{
  "status": "ok"
}
```

No authentication is required for this endpoint.

### User Information

Retrieve information about the authenticated user:

```
GET /user
```

Example using curl:

```bash
curl -H 'X-API-Key: your-api-key' http://localhost:8001/user
```

Response:

```json
{
  "id": 1,
  "username": "user123",
  "email": "user@example.com"
}
```

This endpoint requires authentication with an API key.

### Query Processing

Submit a claim or statement for fact-checking:

```
POST /query
```

Request body:

```json
{
  "body": "Your claim text here",
  "sources": ["calculator", "wikipedia", "web_search", "wolframalpha"]
}
```

The `sources` field is optional. If omitted, all available tools will be used.

Example using curl:

```bash
curl -X POST \
  http://localhost:8001/query \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: your-api-key' \
  -d '{"body": "The earth is flat", "sources": ["wikipedia", "web_search"]}'
```

Response:

```json
{
  "verdict": "False",
  "explanation": "...",
  "sources": [
    {
      "name": "wikipedia",
      "content": "..."
    },
    {
      "name": "web_search",
      "content": "..."
    }
  ],
  "metadata": {
    "processing_time": "..."
  }
}
```

This endpoint requires authentication with an API key and is subject to rate limiting.

### Available Built-in Tools

Get the list of available built-in tools:

```
GET /tools/builtins
```

Example using curl:

```bash
curl -H 'X-API-Key: your-api-key' http://localhost:8001/tools/builtins
```

Response:

```json
{
  "tools": [
    { "name": "calculator", "display_name": "Calculator" },
    { "name": "wikipedia", "display_name": "Wikipedia" },
    { "name": "web_search", "display_name": "Web Search" },
    { "name": "wolframalpha", "display_name": "Wolfram Alpha" }
  ]
}
```

This endpoint requires authentication with an API key.

### Set Tool Preferences

Set preferred tools for the authenticated user:

```
POST /tools/preferences
```

Request body:

```json
{
  "tools": ["wikipedia", "web_search"]
}
```

Example using curl:

```bash
curl -X POST \
  http://localhost:8001/tools/preferences \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: your-api-key' \
  -d '{"tools": ["wikipedia", "web_search"]}'
```

Response:

```json
{
  "message": "Tool preferences updated successfully."
}
```

This endpoint requires authentication with an API key.

## Custom Tools

In addition to the built-in tools, NewsAgent allows you to define custom tools that can interact with external APIs. This feature enables you to extend the system's capabilities without modifying the core code.

### What Are Custom Tools?

Custom tools are user-defined integrations with external APIs that can be used during fact-checking operations. They enable the system to:

- Retrieve specialized data from third-party APIs
- Access domain-specific knowledge bases
- Incorporate additional verification sources into the fact-checking process

### Defining a Custom Tool

To define a custom tool, you need to provide specifications for how the tool should interact with an external API. The system uses these specifications to create a secure interface that can be used during fact-checking operations.

```
POST /tools/custom
```

Request body:

```json
{
  "name": "pokeapi",
  "method": "GET",
  "url_template": "https://pokeapi.co/api/v2/pokemon/{name}",
  "headers": {
    "Accept": "application/json"
  },
  "docstring": "Get information about a Pokémon from the PokeAPI.\nArgs:\n    name (str): The name of the Pokémon to query, ALWAYS LOWERCASED.\nReturns:\n    list: A list containing the Pokémon's abilities.",
  "target_fields": [
    ["abilities", 0, "ability", "name"],
    ["abilities", 1, "ability", "name"]
  ],
  "param_mapping": {
    "name": {
      "type": "str",
      "for": "url_params"
    }
  }
}
```

Example using curl:

```bash
curl -X POST \
  http://localhost:8001/tools/custom \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: your-api-key' \
  -d '{
  "name": "pokeapi",
  "method": "GET",
  "url_template": "https://pokeapi.co/api/v2/pokemon/{name}",
  "headers": {"Accept": "application/json"},
  "docstring": "Get information about a Pokémon from the PokeAPI.\nArgs:\n    name (str): The name of the Pokémon to query, ALWAYS LOWERCASED.\nReturns:\n    list: A list containing the Pokémon'\''s abilities.",
  "target_fields": [["abilities", 0, "ability", "name"], ["abilities", 1, "ability", "name"]],
  "param_mapping": {
    "name": {
      "type": "str",
      "for": "url_params"
    }
  }
}'
```

Response:

```json
{
  "id": 1,
  "name": "pokeapi",
  "created_at": "2023-01-01T00:00:00.000Z",
  "status": "active"
}
```

### Parameters for Custom Tool Definition

When creating a custom tool, you need to specify the following parameters:

| Parameter        | Type   | Required | Description                                                                                 |
| ---------------- | ------ | -------- | ------------------------------------------------------------------------------------------- |
| `name`           | string | Yes      | A unique name for your tool                                                                 |
| `method`         | string | Yes      | The HTTP method to use (GET, POST, PUT, DELETE, PATCH)                                      |
| `url_template`   | string | Yes      | The URL template with placeholders for parameters (e.g., `https://api.example.com/{param}`) |
| `headers`        | object | No       | Default headers to include in the request                                                   |
| `default_params` | object | No       | Default query parameters to include in the request                                          |
| `data`           | object | No       | Default form data to include in the request (for POST/PUT)                                  |
| `json`           | object | No       | Default JSON payload to include in the request (for POST/PUT)                               |
| `docstring`      | string | No       | Documentation for the tool, which helps the system understand how to use it                 |
| `target_fields`  | array  | No       | A list of paths to extract specific fields from the API response                            |
| `param_mapping`  | object | Yes      | Maps function arguments to request components                                               |

#### The `param_mapping` Object

The `param_mapping` object defines the parameters that can be passed to your tool and how they should be used in the API request. Each key in this object represents a parameter name, and its value is an object with:

- `type`: The data type of the parameter (str, int, float, bool, array, object)
- `for`: Where to use this parameter in the request (url_params, params, headers, data, json)

Example:

```json
"param_mapping": {
  "query": {
    "type": "str",
    "for": "params"
  },
  "api_version": {
    "type": "str",
    "for": "url_params"
  },
  "content_type": {
    "type": "str",
    "for": "headers"
  }
}
```

#### The `target_fields` Array

The `target_fields` array allows you to extract specific fields from the API response. Each item in the array is a path to a field in the response JSON. For example, to extract the name of the first ability of a Pokémon:

```json
"target_fields": [["abilities", 0, "ability", "name"]]
```

This would extract the value at `response["abilities"][0]["ability"]["name"]`.

### Examples

#### Simple Weather API Tool

```json
{
  "name": "weather",
  "method": "GET",
  "url_template": "https://api.weather.example/{location}",
  "headers": {
    "Accept": "application/json"
  },
  "docstring": "Get current weather for a location.\nArgs:\n    location (str): City name or zip code.\nReturns:\n    object: Weather information.",
  "param_mapping": {
    "location": {
      "type": "str",
      "for": "url_params"
    }
  }
}
```

#### API with Authentication

```json
{
  "name": "stock_price",
  "method": "GET",
  "url_template": "https://financialdata.example/api/v1/stocks/price",
  "headers": {
    "Accept": "application/json",
    "Authorization": "Bearer your-api-token"
  },
  "docstring": "Get the current price of a stock.\nArgs:\n    symbol (str): Stock ticker symbol.\nReturns:\n    float: Current stock price.",
  "param_mapping": {
    "symbol": {
      "type": "str",
      "for": "params"
    }
  },
  "target_fields": [["data", "price"]]
}
```

### Using Custom Tools in Queries

Once you've defined a custom tool, you can use it in your queries by including it in the `sources` array:

```
POST /query
```

Request body:

```json
{
  "body": "What are Pikachu's abilities?",
  "sources": ["pokeapi", "wikipedia"]
}
```

This will use both your custom "pokeapi" tool and the built-in "wikipedia" tool to answer the query.

### Managing Custom Tools

#### Listing Your Custom Tools

```
GET /tools/custom
```

Example using curl:

```bash
curl -H 'X-API-Key: your-api-key' http://localhost:8001/tools/custom
```

Response:

```json
[
  {
    "id": 1,
    "name": "pokeapi",
    "method": "GET",
    "url_template": "https://pokeapi.co/api/v2/pokemon/{name}",
    "created_at": "2023-01-01T00:00:00.000Z",
    "last_used_at": "2023-01-02T00:00:00.000Z"
  }
]
```

#### Deleting a Custom Tool

```
DELETE /tools/custom/{tool_id}
```

Example using curl:

```bash
curl -X DELETE -H 'X-API-Key: your-api-key' http://localhost:8001/tools/custom/1
```

Response:

```json
{
  "message": "Custom tool deleted successfully"
}
```

### Security Considerations for Custom Tools

- Custom tools are only accessible to the user who created them
- API credentials or tokens included in your custom tool definition are encrypted in the database
- The system does not allow custom tools to execute arbitrary code
- For security reasons, certain domains may be blocked from use with custom tools
- We recommend using environment variables or secure storage for sensitive API keys rather than hardcoding them in your tool definitions

## Security Considerations

- Keep your API keys secure and do not share them with others.
- API keys are stored securely in the database and cannot be retrieved after creation. If you lose your API key, you will need to create a new one.
- API keys do not expire, but they can be deactivated or deleted if needed.
- If you suspect that an API key has been compromised, delete it immediately and create a new one.
