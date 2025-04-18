import os
import wolframalpha
from langchain_core.tools import tool

WOLFRAM_APP_ID_NAME = "WOLFRAM_APP_ID"


@tool("wolframalpha", parse_docstring=True)
def tool_function(query_input: str) -> str:
    """
    Queries Wolfram Alpha to ask questions it can answer, returning the best textual result.

    This function uses the Wolfram Alpha API to interpret and evaluate queries in natural language,
    mathematical expressions, or other formats.

    When to Use Wolfram Alpha Over a Regular Calculator:
        * If your query involves advanced mathematics (e.g., integrals,
          derivatives, polynomial factorization), Wolfram Alpha is more capable than a basic
          calculator.
        * Wolfram Alpha can handle factual, historical, and scientific queries
          that a standard calculator cannot, such as “population of France” or “distance to the Moon.”

    Args:
        query_input (str):
            The query or question to be sent to Wolfram Alpha. This can be a mathematical expression
            (e.g., "solve x^2 + 2x + 1 = 0"), a factual question (e.g., "Who was the 16th President
            of the United States?"), or a natural language inquiry (e.g., "What is the population
            of France?").

    Returns:
        str:
            A human-readable string containing the Wolfram Alpha response.
    """
    if WOLFRAM_APP_ID_NAME not in os.environ:
        return "Wolfram Alpha API key not set up!"
        # Create an APP ID here https://developer.wolframalpha.com/access for the full results API and set as an env var
    try:
        result = wolframalpha.Client(
            os.environ[WOLFRAM_APP_ID_NAME]).query(query_input)
    except Exception:
        return "Unable to query Wolfram Alpha!"
    try:
        return str(next(result.results).text)
    except StopIteration:
        return f"No results on Wolfram Alpha for {query_input}!"


if __name__ == "__main__":
    a = tool_function("erbwdsfmvoms")
    print(a)
