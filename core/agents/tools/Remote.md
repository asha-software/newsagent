# RemoteTool

A tool for connecting to remote API endpoints with support for mock responses during testing.

## Overview

RemoteTool allows you to:
- Connect to remote API endpoints
- Register methods that map to API endpoints
- Use mock responses for testing
- Make real API calls in production

## Function-Based API

```python
from core.agents.tools.remote_tool import create_remote_tool, get_available_methods, get_method_info

# Define methods for the weather API
weather_methods = {
    "get_current_weather": {
        "description": "Get current weather for a location",
        "input_types": [str],  # City name
        "mock_response": {
            "temperature": 22,
            "conditions": "Sunny",
            "humidity": 45
        }
    },
    "get_forecast": {
        "description": "Get 5-day forecast for a location",
        "input_types": [str],  # City name
        "mock_response": [
            {"day": "Monday", "high": 24, "low": 18, "conditions": "Sunny"},
            {"day": "Tuesday", "high": 22, "low": 17, "conditions": "Partly Cloudy"}
            # ... more days
        ]
    }
}

# Create the tool (mock mode for testing)
weather_tool = create_remote_tool(
    name="WeatherAPI",
    url="https://api.weather.example.com",
    api_key="abc123",
    mock=True,  # Use mock mode for testing
    mock_methods=weather_methods
)

# Use the tool
current = weather_tool.use_tool("get_current_weather", ["San Francisco"])
print(current)  # {"temperature": 22, "conditions": "Sunny", "humidity": 45}

forecast = weather_tool.use_tool("get_forecast", ["New York"])
print(forecast[0])  # {"day": "Monday", "high": 24, "low": 18, "conditions": "Sunny"}

# Get available methods
methods = get_available_methods()
print(methods)  # ["get_current_weather", "get_forecast"]

# Get method info
method_info = get_method_info("get_current_weather")
print(method_info["description"])  # "Get current weather for a location"

# For production use, switch to real API mode
production_tool = create_remote_tool(
    name="WeatherAPI",
    url="https://api.weather.example.com",
    api_key="REAL_API_KEY",
    mock=False,
    mock_methods=weather_methods  # Still needed to register methods
)
```

## How It Works

1. When initialized, RemoteTool registers the provided methods
2. For each method, a function is created that handles the method call
3. When `use_tool()` is called:
   - In mock mode: Returns the pre-defined mock response
   - In real mode: Makes an HTTP request to the API endpoint

## API Reference

```python
create_remote_tool(
    name: str,           # Name of the tool
    url: str,            # Base URL for the API
    api_key: str = None, # API key (optional)
    mock: bool = True,   # Whether to use mock mode
    mock_methods: Dict[str, Any] = None  # Method definitions
) -> tool

get_available_methods() -> List[str]  # Get list of available methods

get_method_info(method_name: str) -> Dict[str, Any]  # Get info about a method
```

## Method Definition Format

```python
{
    "method_name": {
        "description": str,  # Description of what the method does
        "input_types": List[type],  # List of parameter types
        "mock_response": Any  # Response to return in mock mode
    }
}
