import json
import wikipedia as wiki
from langchain_core.tools import tool
from core.agents.tools.builtins import tool_registry_globals
from core.agents.utils.common_types import Evidence


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
        str: Information from the wiki page
    """

    # Use our user agent
    wiki.USER_AGENT = tool_registry_globals.USER_AGENT
    try:
        # See if we can find a page
        results: tuple[list[str], str] = wiki.search(
            query_str, results=10, suggestion=1
        )
    except wiki.exceptions.wikiException as e:
        message = f"Could not search {query_str} from wiki!"
        evidence_list = [
            Evidence(
                name="wiki",
                args={"query": query_str},
                content=message,
                source="wiki",
            )
        ]
        str_content = json.dumps(evidence_list)
        return str_content, evidence_list

    title: str
    if results[0]:
        # Use the first search result if one exists
        title = results[0][0]
        print(f"Using first search result {title}!")
    elif results[1] and results[1] is not None:
        # Use the search suggestion if one exists
        title = results[1]
        print(f"Using search suggestion {title}")
    else:
        message = f"Could not find a page for {query_str}!"
        evidence_list = [
            Evidence(
                name="wiki",
                args={"query": query_str},
                content=message,
                source="wiki",
            )
        ]
        return json.dumps(evidence_list), evidence_list
    try:
        # Pull the page from wiki
        page: wiki.wikiPage = wiki.page(
            title, auto_suggest=False, redirect=True
        )
    except wiki.exceptions.wikiException:
        message = f"Could not fetch page title {title} from wiki!"
        evidence_list = [
            Evidence(
                name="wiki",
                args={"query": query_str},
                content=message,
                source="wiki",
            )
        ]
        return json.dumps(evidence_list), evidence_list

    content = page.content
    source = page.url

    evidence_list = [
        Evidence(
            name="wiki",
            args={"query": query_str},
            content=content,
            source=source,
        )
    ]
    return json.dumps(evidence_list), evidence_list


if __name__ == "__main__":
    print(tool_function.invoke("Apple Podcasts"))
