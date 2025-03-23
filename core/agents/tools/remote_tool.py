import json
import requests
from typing import Dict, Any, List
from tool_base import tool


class RemoteTool(tool):
    """
    Connects to a remote API endpoint.
    
    RemoteTool provides a flexible interface for interacting with remote APIs.
    It supports both mock mode for testing and real API calls for production use.
    Users can define methods that map to API endpoints and provide mock responses
    for testing purposes.
    
    Attributes:
        url (str): Base URL of the remote API
        api_key (str, optional): API key for authentication
        mock (bool): Whether to use mock data or make real API calls
        available_methods (Dict[str, Any]): Dictionary of registered methods
    """
    def __init__(self, name: str, url: str, api_key: str = None, mock: bool = True, mock_methods: Dict[str, Any] = None):
        """
        Initialize the RemoteTool.
        
        Args:
            name: Name of the tool
            url: URL of the remote API
            api_key: API key for authentication (optional)
            mock: Whether to use mock data (True) or make real API calls (False)
            mock_methods: Dictionary of mock methods and their responses (required if mock=True)
        """
        super().__init__(name)
        self.url = url
        self.api_key = api_key
        self.mock = mock
        self.available_methods = {}
        
        if mock and not mock_methods:
            raise ValueError("mock_methods must be provided when mock=True")
        
        if mock_methods:
            self.setup_methods(mock_methods)
    
    def setup_methods(self, mock_methods: Dict[str, Any]):
        """
        Set up the available methods.
        
        Iterates through the provided dictionary of mock methods and registers
        each method with the tool.
        
        Args:
            mock_methods: Dictionary of mock methods and their responses
        """
        for method_name, method_info in mock_methods.items():
            self.register_method(method_name, method_info)
    
    def register_method(self, method_name: str, method_info: Dict[str, Any]):
        """
        Register a method as a tool function.
        
        Creates a function that will handle calls to this method and registers
        it with the tool base class. The function will either return mock data
        or make a real API call depending on the tool's configuration.
        
        Args:
            method_name: Name of the method
            method_info: Dictionary containing method information including:
                - description: Description of what the method does
                - input_types: List of parameter types
                - mock_response: Response to return in mock mode
        """
        self.available_methods[method_name] = method_info
        
        def method_function(*args):
            if len(args) != len(method_info["input_types"]):
                return f"Error: Expected {len(method_info['input_types'])} arguments, got {len(args)}"
            
            if self.mock:
                return method_info["mock_response"]
            else:
                try:
                    endpoint = f"{self.url}/{method_name}"
                    headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
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
        
        self.register_tool_function(
            method_info["input_types"],
            method_function,
            method_info["description"]
        )
    
    def get_available_methods(self) -> List[str]:
        """
        Get a list of available methods on the remote end.
        
        Returns:
            List of method names that have been registered with this tool
        """
        return list(self.available_methods.keys())
    
    def get_method_info(self, method_name: str) -> Dict[str, Any]:
        """
        Get information about a specific method.
        
        Args:
            method_name: Name of the method to get information about
            
        Returns:
            Dictionary with method information including description,
            input types, and mock response. Returns an error dictionary
            if the method is not found.
        """
        if method_name in self.available_methods:
            return self.available_methods[method_name]
        return {"error": f"Method '{method_name}' not found"}
