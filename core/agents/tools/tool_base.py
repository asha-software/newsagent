import collections
from typing import Any, Callable


# No structs in Python
class tool_function:
    def __init__(
        self,
        tool_function_name: str,
        input_types: collections.abc.Sequence[type],
        description: str,
        action: Callable,
    ):
        self.tool_function_name = tool_function_name
        self.description = description
        self.input_types = input_types
        self.input_length = len(input_types)
        self.action = action


class tool:
    def __init__(self, datasource_name: str):
        self.datasource_name = datasource_name
        self.registered_tools = {}

    def register_tool_function(
        self,
        input_types: collections.abc.Sequence[type],
        action: Callable,
        description: str,
    ):
        tool_function_name = action.__name__
        self.registered_tools[tool_function_name] = tool_function(
            tool_function_name, input_types, description, action
        )

    def use_tool(self, tool_name, query_arguments: collections.abc.Sequence) -> Any:
        if tool_name in self.registered_tools:
            tool_function_descriptor: tool_function = self.registered_tools[tool_name]
            if len(query_arguments) != tool_function_descriptor.input_length:
                print(
                    f"Input length mismatch error! Given input ${query_arguments} does not match expected length ${tool_function_descriptor.input_length} for types ${tool_function_descriptor.input_types}"
                )
                return
            for iterator in range(tool_function_descriptor.input_length):
                if issubclass(
                    tool_function_descriptor.input_types[iterator],
                    query_arguments[iterator],
                ):
                    print(
                        f"Input length mismatch error! Given input ${query_arguments} does not match expected types ${tool_function_descriptor.input_types}"
                    )
                    return
            return tool_function_descriptor.action(*query_arguments)
