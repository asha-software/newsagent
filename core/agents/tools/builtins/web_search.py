from langchain_core.tools import tool
from tavily import TavilyClient
from typing import Literal
import os
from core.agents.utils.common_types import Evidence


@tool("web_search", parse_docstring=True)
def tool_function(query: str, topic: Literal["general", "news", "finance"]) -> list[Evidence]:
    """
    Search the web. Use this when the claim refers to:
      - current events
      - living public figures
      - recent announcements
      - social media activity
      - trends

    Args:
        query (str): The search term to query. Example: "latest technology trends" or "stock market updates".
        topic (Literal["general", "news", "finance"]): The category of the search. Use "general" for broad or miscellaneous topics, "news" for current events or breaking news, or "finance" for financial information or market insights.

    Returns:
        list: A list of dictionaries containing the content and source URL of the search results.

    Example Usage:
        web_search("are cellphones always listening", topic="general")
        web_search("Tesla stock price", topic="finance")
        web_search("Ukraine war updates", topic="news")
    """
    # Set up Tavily client
    api_key = os.getenv("TAVILY_API_KEY")
    assert api_key, "TAVILY_API_KEY must be set in the environment variables"
    client = TavilyClient(api_key=api_key)

    try:
        response = client.search(
            query,
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

    # Filter out metadata, format results for Evidence
    return [
        Evidence(
            name="web_search",
            args={"query": query, "topic": topic},
            content=res['content'],
            source=res['url']
        )
        for res in response['results']
    ]


if __name__ == "__main__":
    # Test the function
    results = tool_function.invoke(
        {"query": "Who lives in Gracie Mansion?", "topic": "general"})
    from pprint import pprint
    pprint(results)
