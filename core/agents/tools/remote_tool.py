import json
import requests
from typing import Dict, Any, List
from core.agents.tools.tool_base import tool
from langchain_core.tools import tool as langchain_tool

_available_methods = {}

def create_remote_tool(name: str, url: str, api_key: str = None, mock: bool = True, mock_methods: Dict[str, Any] = None, use_langchain: bool = False):
    """
    Create a remote tool that connects to a remote API endpoint.
    
    Args:
        name: Name of the tool
        url: URL of the remote API
        api_key: API key for authentication (optional)
        mock: Whether to use mock data (True) or make real API calls (False)
        mock_methods: Dictionary of mock methods and their responses (required if mock=True)
        use_langchain: Whether to return a langchain Tool (True) or a custom tool (False)
        
    Returns:
        A tool instance configured with the specified methods
    """
    if mock and not mock_methods:
        raise ValueError("mock_methods must be provided when mock=True")
    
    if use_langchain:
        # For langchain compatibility, return the remote_tool function directly
        # This allows it to be used with langchain agents
        return remote_tool
    else:
        # For custom tool usage, return a tool instance
        remote_tool_instance = tool(name)
        
        if mock_methods:
            setup_methods(remote_tool_instance, url, api_key, mock, mock_methods)
        
        return remote_tool_instance

def setup_methods(tool_instance: tool, url: str, api_key: str, mock: bool, mock_methods: Dict[str, Any]):
    """
    Set up the available methods for a remote tool.
    
    Args:
        tool_instance: The tool instance to register methods with
        url: URL of the remote API
        api_key: API key for authentication
        mock: Whether to use mock data or make real API calls
        mock_methods: Dictionary of mock methods and their responses
    """
    global _available_methods
    
    for method_name, method_info in mock_methods.items():
        register_method(tool_instance, method_name, method_info, url, api_key, mock)
        if method_name not in _available_methods:
            _available_methods[method_name] = method_info

def register_method(tool_instance: tool, method_name: str, method_info: Dict[str, Any], url: str, api_key: str, mock: bool):
    """
    Register a method as a tool function.
    
    Args:
        tool_instance: The tool instance to register the method with
        method_name: Name of the method
        method_info: Dictionary containing method information
        url: URL of the remote API
        api_key: API key for authentication
        mock: Whether to use mock data or make real API calls
    """
    def method_function(*args):
        if len(args) != len(method_info["input_types"]):
            return f"Error: Expected {len(method_info['input_types'])} arguments, got {len(args)}"
        
        if mock:
            return method_info["mock_response"]
        else:
            try:
                endpoint = f"{url}/{method_name}"
                headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
                data = {}
                for i, arg_type in enumerate(method_info["input_types"]):
                    data[f"arg{i}"] = args[i]
                
                response = requests.post(endpoint, json=data, headers=headers)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                return {"error": str(e)}
    
    method_function.__doc__ = method_info["description"]
    method_function.__name__ = method_name
    
    # Register with the custom tool system
    tool_instance.register_tool_function(
        method_info["input_types"],
        method_function,
        method_info["description"]
    )
    
    # Also make it available as a standalone function that can be used with langchain
    # This is done by adding it to the global namespace with the langchain_tool decorator
    globals()[method_name] = langchain_tool(description=method_info["description"])(method_function)

def get_available_methods() -> List[str]:
    """
    Get a list of available methods on the remote end.
    
    Returns:
        List of method names that have been registered
    """
    global _available_methods
    return list(_available_methods.keys())

def get_method_info(method_name: str) -> Dict[str, Any]:
    """
    Get information about a specific method.
    
    Args:
        method_name: Name of the method to get information about
        
    Returns:
        Dictionary with method information including description,
        input types, and mock response. Returns an error dictionary
        if the method is not found.
    """
    global _available_methods
    if method_name in _available_methods:
        return _available_methods[method_name]
    return {"error": f"Method '{method_name}' not found"}

# Function that can be used with both the @langchain_tool decorator and langchain.agents.Tool
def remote_tool_func(url: str) -> dict:
    """Get information about a news article from a URL.
    
    Args:
        url: URL of the news article to retrieve information about
        
    Returns:
        Dictionary containing article information
    """
    # Define the mock response directly
    return {
        "title": "News Article",
        "author": "John Doe",
        "published_date": "2025-03-22",
        "content": "This is an example news article content."
    }

# Decorated version for use with langchain_core.tools
@langchain_tool(description="Get information about a news article from a URL")
def remote_tool(url: str) -> dict:
    """Get information about a news article from a URL."""
    return remote_tool_func(url)
