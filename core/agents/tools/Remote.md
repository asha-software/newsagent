# RemoteTool

A tool for connecting to remote API endpoints with support for mock responses during testing.

## Overview

RemoteTool allows you to:
- Connect to remote API endpoints
- Register methods that map to API endpoints
- Use mock responses for testing
- Make real API calls in production

## Usage Example

Here's how to create and use a RemoteTool for a weather API:

```python
from core.agents.tools.remote_tool import RemoteTool

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
weather_tool = RemoteTool(
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

# For production use, switch to real API mode
production_tool = RemoteTool(
    name="WeatherAPI",
    url="https://api.weather.example.com",
    api_key="REAL_API_KEY",
    mock=False,
    mock_methods=weather_methods  # Still needed to register methods
)
```

## How It Works

1. When initialized, RemoteTool calls `_setup_methods()` with the provided methods
2. For each method, `_register_method()` is called to:
   - Store method information
   - Create a function that handles the method call
   - Register the function with the tool system

3. When `use_tool()` is called:
   - In mock mode: Returns the pre-defined mock response
   - In real mode: Makes an HTTP request to the API endpoint

## API Reference

### RemoteTool Constructor

```python
RemoteTool(
    name: str,           # Name of the tool
    url: str,            # Base URL for the API
    api_key: str = None, # API key (optional)
    mock: bool = True,   # Whether to use mock mode
    mock_methods: Dict[str, Any] = None  # Method definitions
)
```

### Method Definition Format

```python
{
    "method_name": {
        "description": str,  # Description of what the method does
        "input_types": List[type],  # List of parameter types
        "mock_response": Any  # Response to return in mock mode
    }
}
