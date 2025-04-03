import os
import wolframalpha
import langchain.tools

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
    if WOLFRAM_APP_ID_NAME not in os.environ:
        return "Wolfram Alpha API key not set up!"
        # Create an APP ID here https://developer.wolframalpha.com/access for the full results API and set as an env var
    try:
        result = wolframalpha.Client(os.environ[WOLFRAM_APP_ID_NAME]).query(query_input)
    except Exception:
        return "Unable to query Wolfram Alpha!"
    try:
        return str(next(result.results).text)
    except StopIteration:
        return f"No results on Wolfram Alpha for {query_input}!"


if __name__ == "__main__":
    a = query("erbwdsfmvoms")
    print(a)
