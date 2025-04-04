from langchain_core.tools import tool


@tool("calculator", parse_docstring=True)
def add(a: float, b: float) -> float:
    """Add `a` and `b`

    Args:
        a: First number
        b: Second number

    Returns:
        The sum of `a` and `b`
    """
    return a + b
