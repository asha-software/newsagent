from typing import Any
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


@tool(description="This tool divides two complex numbers.")
def divide(a: numbers.Complex, b: numbers.Complex) -> Any:
    """Divide `a` and `b`

    Args:
        a: First number
        b: Second number
    """
    return a / b


@tool(description="This tool divides two numbers.")
def integer_divide(a: numbers.Integral, b: numbers.Integral) -> int:
    """Divide `a` and `b`, throw away the remainder

    Args:
        a: First number
        b: Second number
    """
    return int(a) // int(b)
