import googlesearch
from tool_base import tool


def perform_search(a: str) -> str:
    return "\n".join(googlesearch.search(a))


class GoogleSearchTool(tool):

    def __init__(self):
        super().__init__("GoogleSearchTool")
        self.register_tool_function(perform_search)


if __name__ == "__main__":
    search_tool = GoogleSearchTool()
    print(search_tool.use_tool("perform_search", ("Google Maps",)))
