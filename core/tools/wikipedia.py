# Create a function that queries Wikipedia

import wikipediaapi

LANGUAGE = "en"
USER_AGENT = user_agent = (
    "newsagent/1.0 (https://ashasoftware.com/newsagent; info@ashasoftware.com)"
)


def query(query: str) -> str:
    """
    This function queries Wikipedia. Use it to retrieve information about historical events or common knowledge.

    Args:
        query (str): The search term to query Wikipedia.

    Returns:
        str: The summary of the Wikipedia page.
    """
    wiki_wiki = wikipediaapi.Wikipedia(user_agent=USER_AGENT, language=LANGUAGE)
    page = wiki_wiki.page(query)

    if page.exists():
        # TODO: be smarter about what parts of the Wikipedia page to return
        return page.summary
    else:
        return f"No Wikipedia page found for '{query}'."


if __name__ == "__main__":
    result = query_wikipedia("Python (programming language)")
    print(result)
