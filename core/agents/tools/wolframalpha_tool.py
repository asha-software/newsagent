import os
import wolframalpha
import langchain.tools
import typeguard

WOLFRAM_APP_ID_NAME = "WOLFRAM_APP_ID"


@langchain.tools.tool()
def query(query_input: str) -> str:
    """
    Query Wolfram Alpha to ask questions it can answer.
    Args:
        query_input (str): The string query you want to ask.

    Returns:
        A string output with the result.
    """
    try:
        # Type check inputs
        typeguard.check_type(query_input, str)
    except TypeError:
        return "Invalid input type!"
    if WOLFRAM_APP_ID_NAME not in os.environ:
        return "Wolfram Alpha API key not set up!"
        # Create an APP ID here https://developer.wolframalpha.com/access for the full results API and set as an env var
    try:
        result = wolframalpha.Client(os.environ[WOLFRAM_APP_ID_NAME]).query(query_input)
    except Exception:
        return "Unable to query Wolfram Alpha!"
    return str(next(result.results).text)


if __name__ == "__main__":
    a = query("what is two plus two")
    print(a)
