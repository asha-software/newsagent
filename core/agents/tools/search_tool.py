from googleseach_with_custom_agent import search
import typeguard
from core.agents.tools import tool_registry
import langchain.tools


@langchain.tools.tool()
def perform_search(search_term: str) -> str:
    """
    Perform a Google Search and get back a response
    Args:
        search_term (str): The term to search on Google.

    Returns:
        A JSON structure comprised of a list of titles and descriptions for each search result
    """
    try:
        # Type check inputs
        typeguard.check_type(search_term, str)
    except TypeError:
        return "Invalid input type!"
    # Perform google search and return a JSON result to the language model
    return "\n\n".join(
        f"Title: {result.title}\nDescription {result.description}"
        for result in search(
            search_term,
            num_results=50,
            advanced=True,
            unique=True,
            user_agent=tool_registry.USER_AGENT,
        )
    )
