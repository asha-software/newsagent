# Create a function that queries Wikipedia

import wikipediaapi
import tool_base


class wikipediaTool(tool_base.tool):

    def query(self, query: str) -> str:
        """
        This function queries Wikipedia. Use it to retrieve information about historical events or common knowledge.

        Args:
            query (str): The search term to query Wikipedia.

        Returns:
            str: The summary of the Wikipedia page.
        """
        wiki_wiki = wikipediaapi.Wikipedia(
            user_agent=self.USER_AGENT, language=self.LANGUAGE
        )
        page = wiki_wiki.page(query)

        if page.exists():
            # TODO: be smarter about what parts of the Wikipedia page to return
            return page.summary
        else:
            return f"No Wikipedia page found for '{query}'."

    def __init__(self):
        super().__init__("wikipedia")
        self.LANGUAGE = "en"
        self.USER_AGENT = (
            "newsagent/1.0 (https://ashasoftware.com/newsagent; info@ashasoftware.com)"
        )
        self.register_tool_function(self.query)


if __name__ == "__main__":
    wikipedia_tool = wikipediaTool()
    print(wikipedia_tool.use_tool("query", ("Ants",)))
