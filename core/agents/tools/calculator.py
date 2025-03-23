from typing import Any
from tool_base import tool
import numbers


def add(a: numbers.Complex, b: numbers.Complex) -> Any:
    """Add `a` and `b`

    Args:
        a: First number
        b: Second number
    """
    return a + b


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


class Calculator(tool):

    def __init__(self):
        super().__init__("Calculator")
        self.register_tool_function(add)
        self.register_tool_function(divide)
        self.register_tool_function(integer_divide)


if __name__ == "__main__":
    c = Calculator()
    print(c.use_tool("add", (1, 14)))
    print(c.use_tool("divide", (1, 2)))
    print(c.use_tool("integer_divide", (1, 2)))
    print(c.use_tool("whoami", tuple()))
