import os
import wolframalpha
import langchain.tools

WOLFRAM_APP_ID_NAME = "WOLFRAM_APP_ID"


@langchain.tools.tool()
def query(query_input: str) -> str:
    """
    Query Wolfram Alpha to ask questions it can answer, returning the best textual result.

    This function relies on the Wolfram Alpha API to parse and evaluate queries in natural language,
    mathematical expressions, or other compatible formats.

    **Args**:
        query_input (str):
            A string containing the query or question you wish to ask Wolfram Alpha. Examples include:
            - Natural language queries (e.g., "What is the population of France?")
            - Mathematical expressions or equations (e.g., "solve x^2 + 2x + 1 = 0")
            - General knowledge queries (e.g., "Who was the 16th President of the United States?")

    **Returns**:
        str:
            A human-readable string containing the Wolfram Alpha response if successful.
            - The text of a Wolfram Alpha result pod (e.g., "Abraham Lincoln").

    **Usage Example**:
         query("What is the derivative of x^2?")
         2x
    **Notes**:
        - The function only returns short textual answers from the primary result pods.
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
