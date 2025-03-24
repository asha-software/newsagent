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
        input_types=None,
        action: Callable = None,
        description: str = None,
    ):
        # Handle both the old and new calling conventions
        if action is None and isinstance(input_types, Callable):
            # Old style: register_tool_function(action)
            action = input_types
            tool_function_name = action.__name__
            self.registered_tools[tool_function_name] = tool_function(action)
        else:
            # New style: register_tool_function(input_types, action, description)
            tool_function_name = action.__name__
            # Create a tool_function instance manually
            tf = tool_function(action)
            # Override the attributes if provided
            if input_types is not None:
                tf.input_types = input_types
                tf.input_length = len(input_types)
            if description is not None:
                tf.description = description
            self.registered_tools[tool_function_name] = tf

    def use_tool(self, tool_name, query_arguments: collections.abc.Sequence) -> Any:
        if tool_name in self.registered_tools:
            tool_function_descriptor: tool_function = self.registered_tools[tool_name]
            if len(query_arguments) != tool_function_descriptor.input_length:
                print(
                    f"Input length mismatch error! Given input {query_arguments} does not match expected length {tool_function_descriptor.input_length} for types {tool_function_descriptor.input_types}"
                )
                return None
            
            return tool_function_descriptor.action(*query_arguments)
        else:
            print(f"Tool '{tool_name}' not found. Available tools: {list(self.registered_tools.keys())}")
            return None
