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
        return [{"name":"temperature_api","url":"https://temperature/api?","params":{"key":"whatever"}}, 
                {"name":"news", "url":"https://nytimes/api","params":"whatever"}]
    else:
        ##@Taufique please add code here
        return
        
def construct_url(tool_dict):
    '''
    Construct a new URL based on the key-value pairs in tool_dict.
    Args:
        tool_dict: Dictionary containing API data (expects "url" and "params").
    Returns:
        A new URL string.
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
    if url =="https://temperature/api?key=whatever":
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
    
