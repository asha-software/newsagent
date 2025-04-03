import math
import numexpr
from langchain_core.tools import tool


@tool
def calculator(expression: str) -> str:
    """Calculate expression.
    Expression should be a single line mathematical expression.

    Examples:
        "37593 * 67" for "37593 times 67"
        "37593**(1/5)" for "37593^(1/5)"
    """
    local_dict: dict[str, float] = {"pi": math.pi, "e": math.e, "tau": math.tau}
    try:
        return str(
            numexpr.evaluate(
                expression.strip().lower(),
                global_dict={},  # restrict access to globals
                local_dict=local_dict,  # add common mathematical functions
            )
        )
    except SyntaxError:
        return "Invalid expression!"

if __name__ == "__main__":
    print(calculator("37593 * 67"))
