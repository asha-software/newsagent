import collections
import inspect
from typing import Callable, get_type_hints, Any


# No structs in Python
class tool_function:
    def __init__(
        self,
        action: Callable,
    ):
        self.tool_function_name = action.__name__
        self.description: str = str(inspect.getdoc(action))
        type_hints: dict[str, Any] = get_type_hints(action)
        type_hints.pop("return", None)
        self.input_types: tuple = tuple(type_hints.values())
        self.input_length = len(self.input_types)
        self.action = action


class tool:
    def __init__(self, datasource_name: str):
        self.datasource_name = datasource_name
        self.registered_tools = {}

    def register_tool_function(
        self,
        action: Callable,
    ):
        tool_function_name = action.__name__
        self.registered_tools[tool_function_name] = tool_function(action)

    def use_tool(self, tool_name, query_arguments: collections.abc.Sequence) -> str:
        if tool_name not in self.registered_tools:
            return f"Tool name {tool_name} not registered"
        tool_function_descriptor: tool_function = self.registered_tools[tool_name]
        if len(query_arguments) != tool_function_descriptor.input_length:
            return f"Input length mismatch error! Given input {query_arguments} does not match expected length {tool_function_descriptor.input_length} for types {tool_function_descriptor.input_types}"
        for iterator in range(tool_function_descriptor.input_length):
            if not issubclass(
                type(query_arguments[iterator]),
                tool_function_descriptor.input_types[iterator],
            ):
                return f"Input type mismatch error! Given input {query_arguments} does not match expected types {tool_function_descriptor.input_types}"
        return str(tool_function_descriptor.action(*query_arguments))
