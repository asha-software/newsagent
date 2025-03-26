import json
import requests
from typing import Dict, Any, List

def fetch_tools(user_id):
    '''
    Fetch user registered api tools
    Args:
        user_id: string
    Returns:
        a list of dictionaries. each dictionary has api name and api url
    '''
    if user_id=="123":
        return [{"name":"temperature_api","url":"https://temperature/api?","params":{"key":"whatever",'q':''}}, 
                {"name":"news", "url":"https://nytimes/api","params":{"key":"whatever"}}]
    else:
        ##@Taufique please add code here
        return
        
def construct_url(tool_dict):
    '''
    Construct a full URL from a tool dictionary and a query string.

    This function takes two arguments:
    1. `tool_dict` (dict or str): A dictionary or JSON string representing the tool, which must contain:
        - 'name' (str): The tool's name.
        - 'url' (str): The base URL.
        - 'params' (dict): Optional parameters to include in the query string (key-value pairs).

    The function builds a complete URL by appending parameters to the base URL.

    Args:
        tool_dict (dict or str): A dictionary representing the tool (or a JSON string that can be parsed into a dictionary).

    Returns:
        str: The full URL with the appended query parameters.

    Raises:
        ValueError: If `tool_dict` is neither a valid dictionary nor a valid JSON string.
        ValueError: If `tool_dict` is missing required fields like 'url' or 'params'.
    '''
    # Ensure input is a dictionary
    if isinstance(tool_dict, str):
        try:
            tool_dict = json.loads(tool_dict)
        except json.JSONDecodeError:
            raise ValueError("construct_url expects a dictionary or a valid JSON string!")

    if not isinstance(tool_dict, dict):
        raise ValueError("construct_url expects a dictionary, not a string!")

    # Extract URL and params
    url = tool_dict.get("url", "")
    params = tool_dict.get("params", {})

    # Build query string
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    if query_string:
        url += query_string

    return url
    
def remote_api_call(url):
    '''
    ping the api url with the parameters
    args:
        url: url string
        params: parameters, string
    Returns:
         Dictionary containing api response.
    '''
    if url =="https://temperature/api?key=whatever&q=temperature":
        return {"temperature":20}
    else:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()  # Return the JSON data from the API response
        else:
            return f"Error: {response.status_code}"

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
    
