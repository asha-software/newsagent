from tool_base import tool

import numbers


def add(a: numbers.Complex, b: numbers.Complex) -> numbers.Complex:
    """Add `a` and `b`

    Args:
        a: First number
        b: Second number
    """
    return a + b


def divide(a: numbers.Real, b: numbers.Real) -> float:
    """Divide `a` and `b`

    Args:
        a: First number
        b: Second number
    """
    return a / b




class Calculator(tool):

    def integer_divide(self, a: int, b: int) -> int:
        """Divide `a` and `b`, throw away the remainder

        Args:
            a: First number
            b: Second number
        """
        return a // b

    def __init__(self):
        super().__init__("Calculator")
        self.register_tool_function((int, int), add, add.__doc__)
        self.register_tool_function((float, float), divide, divide.__doc__)
        self.register_tool_function((float, float), self.integer_divide, self.integer_divide.__doc__)

tool_registry["Calculator"].use_tool("add", [1, 2])
