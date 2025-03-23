from typing import Any
from .tool_base import tool
import numbers
from langchain_core.tools import tool

@tool(description="This tool adds two numbers.")
def add(a: numbers.Complex, b: numbers.Complex) -> Any:
    """Add `a` and `b`

    Args:
        a: First number
        b: Second number
    """
    return a + b

@tool(description="This tool devides two complex numbers.")
def divide(a: numbers.Complex, b: numbers.Complex) -> Any:
    """Divide `a` and `b`

    Args:
        a: First number
        b: Second number
    """
    return a / b


def integer_divide(a: int, b: int) -> int:
    """Divide `a` and `b`, throw away the remainder

    Args:
        a: First number
        b: Second number
    """
    return a // b

@tool(description="Resgister function add, devide and integer_devide detail function instruction, refer to the original function in this script")
class Calculator(tool):
    def __init__(self):
        super().__init__("Calculator")
        '''
        resgister function add, devide and integer_devide
        detail function instruction, refer to the original function in this script
        '''
        self.register_tool_function(add)
        self.register_tool_function(divide)
        self.register_tool_function(integer_divide)


# if __name__ == "__main__":
#     c = Calculator()
#     print(c.use_tool("add", (1, 14)))
#     print(c.use_tool("divide", (1, 2)))
#     print(c.use_tool("integer_divide", (1, 2)))
#     print(c.use_tool("whoami", tuple()))
