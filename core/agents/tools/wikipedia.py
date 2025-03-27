# Queries Wikipedia
import langchain.tools
import wikipediaapi
from typeguard import check_type
from core.agents.tools import tool_registry


@langchain.tools.tool()
def query(query_str: str, language: str = "en") -> str:
    try:
        check_type(query_str, str)
        check_type(language, str)
    except TypeError:
        return "Invalid types for function inputs!"
    """
    This function queries Wikipedia. Use it to retrieve information about historical events or common knowledge.

    Args:
        language (str): The Wikipedia language code to use. Default is en for english.
        query_str (str): The search term to query Wikipedia.

    Returns:
        str: Information from the Wikipedia page
    """
    wiki_wiki = wikipediaapi.Wikipedia(
        user_agent=tool_registry.USER_AGENT, language=language
    )
    page = wiki_wiki.page(query_str)
    if page.exists():
        return f"{page.title}\n{page.summary}\n{page.text}"
    else:
        return f"No Wikipedia page found for '{query_str}'."
