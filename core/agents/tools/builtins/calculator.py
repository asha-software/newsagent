import math
import numpy
import numexpr
from langchain_core.tools import tool
from core.agents.utils.common_types import Evidence


@tool("calculator", parse_docstring=True)
def tool_function(expression: str) -> list[Evidence]:
    """Calculate single-line numeric expressions. Useful for performing quick calculations.

    Args:
        expression (str): A valid mathematical expression in string format. Supports basic operators (+, -, *, /),
                          exponentiation (**), and constants like "pi", "e", "tau", and "euler_gamma".

    Returns:
        str: The result of the calculation as a string, or "Invalid expression!" if the input is invalid.

    Examples:
        - "37593 * 67" (multiplication)
        - "37593**(1/5)" (exponentiation)
        - "pi * 2" (using constants)
    """
    local_dict: dict[str, float] = {
        "pi": math.pi, "e": math.e, "tau": math.tau, "euler_gamma": float(numpy.euler_gamma)}
    try:
        result = str(
            numexpr.evaluate(
                expression.strip().lower(),
                global_dict={},  # restrict access to globals
                local_dict=local_dict,  # add common mathematical functions
            )
        )
        return [
            Evidence(
            name="calculator",
            args={"expression": expression},
            content=result,
            source="calculator",
        )]
    except SyntaxError as e:
        # Log the error for debugging
        print(f"Calculator tool SyntaxError: {e}")
        return [
            Evidence(
            name="calculator",
            args={"expression": expression},
            content="Invalid expression",
            source="calculator",
        )]


if __name__ == "__main__":
    print(tool_function("37593 * 67"))
