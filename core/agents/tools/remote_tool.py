from tool_base import tool


class RemoteTool(tool):
    def __init__(self, name: str, url: str, api_key: str):
        super().__init__(name)
        self.url = url
        self.api_key = api_key
