from langchain_core.tools import tool
from tavily import TavilyClient
from typing import Literal
import os


@tool("web_search", parse_docstring=True)
def web_search_tavily(query: str, topic: Literal["general", "news", "finance"]) -> list[dict]:
    """
    A search engine optimized for comprehensive, accurate, and trusted results. Useful for when you need to answer questions about current events.

    Args:
        query (str): The search term to query.
        topic (str): Use "news" for current events, "finance" for financial information. Otherwise, use "general". 

    Returns:
        list: A list of dictionaries containing the content and source URL of the search results.
    """
    # Set up Tavily client
    api_key = os.getenv("TAVILY_API_KEY")
    assert api_key, "TAVILY_API_KEY must be set in the environment variables"
    client = TavilyClient(api_key=api_key)

    try:
        response = client.search(query,
                                 topic=topic,
                                 max_results=3,
                                 chunks_per_source=4,
                                 include_images=False,
                                 exclude_domains=["wikipedia.org"]

                                 # Other optional parameters:
                                 # include_answer=False, # Can ONLY be set during instantiation
                                 # include_raw_content=False, # Can ONLY be set during instantiation
                                 # include_image_descriptions=False,
                                 # search_depth="basic", # alt: "advanced". Costs 2x more but returns more of the web pages
                                 # time_range="day",
                                 # include_domains=None,
                                 )
    except Exception as e:
        print(f"Error during Tavily search: {e}")
        return []

    # Filter out metadata, format results for Evidence.results
    return [{'content': res['content'], 'source': res['url']} for res in response['results']]


if __name__ == "__main__":
    # Test the function
    results = web_search_tavily.invoke(
        {"query": "Who lives in Gracie Mansion?", "topic": "general"})
    for result in results:
        print(f"Content: {result['content']}")
        print(f"Source: {result['source']}")
        print()
