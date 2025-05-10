import json
import wikipedia as wiki
from langchain_core.tools import tool
from core.agents.tools.builtins import tool_registry_globals
from core.agents.utils.common_types import Evidence

REFERENCE_SECTION_NAMES = {
    "See also",
    "Notes",
    "References",
    "Further reading",
    "External links",
}

"""
README: Using this wikipedia module we first enter a query string in `wiki.search()`. This returns a list of page titles.
We then iterate over the page titles and fetch the content of each page using `wiki.page()`.
We also check for sections in the page and add them to the content if they are not in the REFERENCE_SECTION_NAMES, which we assume
are not relevant for the user.
"""


@tool("wikipedia", parse_docstring=True, response_format="content_and_artifact")
def tool_function(query_str: str) -> tuple[str, list[Evidence]]:
    """
    Query wiki. Use it to get factual information on:
    - historical figures, events, or places
    - scientific concepts
    - common knowledge
    - debunked myths

    Args:
        query_str (str): The search term to query wiki.

    Returns:
        list[str]: Information from the wikipedia pages related to the query.
    """

    # Use our user agent
    wiki.USER_AGENT = tool_registry_globals.USER_AGENT

    content = None
    page_titles = []
    evidence_list = []

    try:
        page_titles = wiki.search(query_str, results=2)
    except wiki.exceptions.wikiException as e:
        print(f"Error searching Wikipedia for '{query_str}': {e}")

    if not page_titles:
        evidence_list = [
            Evidence(
                name="wikipedia",
                args={"query": query_str},
                content=f"Something went wrong searching Wikipedia for '{query_str}'",
                source="wikipedia",
            )
        ]

    # Create an Evidence for each page
    for title in page_titles:
        try:
            page = wiki.page(title=title, auto_suggest=False)
            content = [page.content] + [
                page.section(section_name)
                for section_name in page.sections
                if section_name not in REFERENCE_SECTION_NAMES
            ]
            evidence = Evidence(
                name="wikipedia",
                args={"query": query_str},
                content=content,
                source=page.url,
            )
            evidence_list.append(evidence)
        except Exception as e:
            print(f"Error fetching page '{title}': {e}")

    return json.dumps(evidence_list), evidence_list


if __name__ == "__main__":
    print(tool_function.invoke("Apple Podcasts"))
