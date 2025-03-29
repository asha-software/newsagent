# Queries Wikipedia
import langchain.tools
import wikipedia
from typeguard import check_type
from core.agents.tools import tool_registry


@langchain.tools.tool()
def query(query_str: str) -> str:
    """
    This function queries Wikipedia. Use it to retrieve information about historical events or common knowledge.

    Args:
        query_str (str): The search term to query Wikipedia.

    Returns:
        str: Information from the Wikipedia page
    """
    # Perform type checking
    try:
        check_type(query_str, str)
    except TypeError:
        return "Invalid types for function inputs!"
    # Use our user agent
    wikipedia.USER_AGENT = tool_registry.USER_AGENT
    try:
        # See if we can find a page
        results: tuple[list[str], str] = wikipedia.search(
            query_str, results=10, suggestion=1
        )
    except wikipedia.exceptions.WikipediaException:
        return f"Could not search {query_str} from Wikipedia!"
    title: str
    if results[0]:
        # Use the first search result if one exists
        title = results[0][0]
        print(f"Using first search result {title}!")
    elif results[1] is not None:
        # Use the search suggestion if one exists
        title = results[1]
        print(f"Using search suggestion {title}")
    else:
        return f"No page found for {query_str}!"
    try:
        # Pull the page from wikipedia
        page: wikipedia.WikipediaPage = wikipedia.page(
            title, auto_suggest=False, redirect=True
        )
    except wikipedia.exceptions.WikipediaException:
        return f"Could not fetch page title {title} from Wikipedia!"
    return page.content


if __name__ == "__main__":
    print(query("Apple Podcasts"))
