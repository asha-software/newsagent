from core.agents.tools import tool_base


class tool_registry:
    def __init__(self):
        self.tools: tool_base = []
