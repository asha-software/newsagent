# Building Custom Tools for NewsAgent

This guide explains how to create and use custom tools with NewsAgent's API integration system. Custom tools allow you to extend NewsAgent's capabilities by connecting to external APIs without writing any backend code.

## What Are Custom Tools?

Custom tools enable NewsAgent to interact with third-party APIs during fact-checking operations. You can use them to:

- Retrieve specialized data from domain-specific APIs
- Query knowledge bases that aren't part of NewsAgent's built-in sources
- Add your own verification services to the fact-checking process

## Basic Concepts

A custom tool is essentially a wrapper around an API endpoint. The tool has:

1. A **name** that NewsAgent uses to reference it
2. An **API endpoint** configuration (URL, HTTP method, headers, etc.)
3. **Parameters** that users can specify when using the tool
4. A **response parser** that extracts specific information from API responses

## Creating a Custom Tool

### Core Parameters

| Parameter        | Description                                           | Required    |
| ---------------- | ----------------------------------------------------- | ----------- |
| `name`           | Unique identifier for your tool                       | Yes         |
| `method`         | HTTP method (`GET`, `POST`, `PUT`, `DELETE`, `PATCH`) | Yes         |
| `url_template`   | URL with optional placeholders like `{param_name}`    | Yes         |
| `param_mapping`  | Definition of parameters and where to use them        | Yes         |
| `docstring`      | Documentation for the AI about how to use the tool    | Recommended |
| `headers`        | HTTP headers to include with requests                 | Optional    |
| `default_params` | Default query string parameters                       | Optional    |
| `data`           | Form data for POST requests                           | Optional    |
| `json`           | JSON payload for POST requests                        | Optional    |
| `target_fields`  | Paths to extract from the response                    | Optional    |

### Parameter Mapping

The `param_mapping` object defines what parameters your tool accepts and how they're used in requests:

```json
{
  "param_name": {
    "type": "str", // Data type: str, int, float, bool, array, object
    "for": "url_params" // Where to use it: url_params, params, headers, data, json
  }
}
```

Possible values for `"for"`:

- `"url_params"`: Replace placeholders in the URL template
- `"params"`: Add as query string parameters
- `"headers"`: Include in request headers
- `"data"`: Add to form data (for POST/PUT requests)
- `"json"`: Include in JSON body (for POST/PUT requests)

### Response Extraction

Use `target_fields` to extract specific data from the API response:

```json
"target_fields": [["results", 0, "value"], ["metadata", "timestamp"]]
```

This example would extract two values:

- `response["results"][0]["value"]`
- `response["metadata"]["timestamp"]`

## Example: Weather API Tool

Here's a complete example of a weather API tool:

```json
{
  "name": "weather_api",
  "method": "GET",
  "url_template": "https://api.weatherapi.com/v1/current.json",
  "headers": {
    "Accept": "application/json"
  },
  "default_params": {
    "key": "YOUR_API_KEY"
  },
  "param_mapping": {
    "location": {
      "type": "str",
      "for": "params"
    }
  },
  "docstring": "Get current weather for a location.\nArgs:\n    location (str): City name, ZIP code, or coordinates\nReturns:\n    dict: Current temperature and conditions",
  "target_fields": [
    ["current", "temp_c"],
    ["current", "condition", "text"]
  ]
}
```

## Example: Stock Price API

```json
{
  "name": "stock_price",
  "method": "GET",
  "url_template": "https://api.marketdata.com/v1/stocks/{symbol}/price",
  "headers": {
    "Authorization": "Bearer YOUR_API_KEY",
    "Content-Type": "application/json"
  },
  "docstring": "Get the current price of a stock by its ticker symbol.\nArgs:\n    symbol (str): The stock ticker symbol (e.g., AAPL, MSFT)\nReturns:\n    float: The current stock price",
  "param_mapping": {
    "symbol": {
      "type": "str",
      "for": "url_params"
    }
  },
  "target_fields": [["data", "price"]]
}
```

## Advanced: POST Request with JSON Body

```json
{
  "name": "sentiment_analysis",
  "method": "POST",
  "url_template": "https://api.nlp-service.com/analyze",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "ApiKey YOUR_API_KEY"
  },
  "param_mapping": {
    "text": {
      "type": "str",
      "for": "json"
    },
    "language": {
      "type": "str",
      "for": "json"
    }
  },
  "docstring": "Analyze the sentiment of a text passage.\nArgs:\n    text (str): The text to analyze\n    language (str): The language code (e.g., 'en')\nReturns:\n    dict: Sentiment scores including positive, negative, and neutral values",
  "target_fields": [["sentiment"]]
}
```

## Best Practices

1. **Meaningful Names**: Choose descriptive names for your tools and parameters.

2. **Comprehensive Docstrings**: Write clear docstrings that explain:

   - What the tool does
   - What each parameter is for (with examples)
   - What the return value contains

3. **Error Handling**: Test your tools with various inputs to ensure they handle errors gracefully.

4. **API Security**: Never embed sensitive API keys directly in your tool definition. Consider:

   - Using environment variables for API keys
   - Setting up a proxy API if the third-party API requires complex authentication

5. **Response Targeting**: Use `target_fields` to extract only the necessary data and reduce noise.

## Technical Details

### Type Mapping

The following types are supported for parameters:

- `"str"`: String values
- `"int"`: Integer values
- `"float"`: Floating-point numbers
- `"bool"`: Boolean values
- `"array"`: Lists/arrays
- `"object"`: Dictionaries/objects

### URL Templates

URL templates support Python's string formatting syntax for placeholders:

```
https://api.example.com/users/{user_id}/posts/{post_id}
```

When `user_id` and `post_id` parameters are provided with `"for": "url_params"`, they will be inserted into these placeholders.

### Extracting Complex Data

For complex API responses, you can use multiple `target_fields` paths to extract different pieces of data. For example:

```json
"target_fields": [
  ["weather", "temperature"],
  ["weather", "humidity"],
  ["forecast", 0, "conditions"],
  ["forecast", 1, "conditions"]
]
```

This would extract four separate values from the API response.

## Using Custom Tools in NewsAgent

Once you've defined a custom tool, you can use it in your fact-checking queries by including it in the `sources` array:

```json
{
  "body": "Is it raining in London right now?",
  "sources": ["weather_api", "web_search"]
}
```

This would use both your custom `weather_api` tool and the built-in `web_search` tool to answer the query.
