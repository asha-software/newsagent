import requests
from django.conf import settings

def get_builtin_tools():
    """
    Get the list of built-in tools from the API container.
    If the API call fails, fall back to hardcoded tools.
    
    Returns:
        list: A list of dictionaries containing tool information (name, value).
    """
    tools = []
    
    # Define a list of hardcoded tools to use as a fallback
    hardcoded_tools = [
        {"name": "calculator", "display_name": "Calculator"},
        {"name": "wikipedia", "display_name": "Wikipedia"},
        {"name": "web_search", "display_name": "Web Search"},
        {"name": "wolfram_alpha", "display_name": "Wolfram Alpha"}
    ]
    
    # Try to get the list of built-in tools from the API container
    try:
        # Get the API URL from settings
        api_url = settings.API_URL
        if not api_url:
            raise ValueError("API_URL is not set in settings")
        
        # First, let's try to make a simple API call to check if the API is available
        try:
            health_response = requests.get(f"{api_url}/health", timeout=5)
            health_response.raise_for_status()
        except Exception as e:
            raise ValueError(f"API health check failed: {e}")
        
        # Now, let's make an API call to get the list of built-in tools
        try:
            tools_response = requests.get(f"{api_url}/tools/builtins", timeout=5)
            tools_response.raise_for_status()
            tools_data = tools_response.json()
            
            if "tools" in tools_data and tools_data["tools"]:
                tools = tools_data["tools"]
            else:
                raise ValueError("No tools found in API response")
        except Exception as e:
            raise ValueError(f"Error getting built-in tools from API: {e}")
        
        if tools:
            return tools
        else:
            raise ValueError("No tools found in API container")
    except Exception:
        # Fall back to hardcoded tools if there's any error
        return hardcoded_tools
