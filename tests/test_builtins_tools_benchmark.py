import pytest
import time
from core.agents.tools.builtins.calculator import tool_function as calculator_tool
from core.agents.tools.builtins.wikipedia import tool_function as wikipedia_tool
from core.agents.tools.builtins.web_search import tool_function as web_search_tool
from core.agents.tools.builtins.wolframalpha import tool_function as wolframalpha_tool

@pytest.mark.benchmark
def test_calculator_benchmark():
    """Benchmark the calculator tool."""
    expression = "37593 * 67"
    start_time = time.time()
    result = calculator_tool.invoke({"expression": expression})
    end_time = time.time()

    elapsed_time = end_time - start_time
    print(f"Elapsed time for calculator tool: {elapsed_time:.2f} seconds")
    print(f"Result: {result}")

    assert result is not None, "Calculator tool returned no result"
    assert elapsed_time < 5, "Calculator tool took too long"

@pytest.mark.benchmark
def test_wikipedia_benchmark():
    """Benchmark the wikipedia tool."""
    query = "Apple Podcasts"
    start_time = time.time()
    result = wikipedia_tool.invoke({"query_str": query})
    end_time = time.time()

    elapsed_time = end_time - start_time
    print(f"Elapsed time for wikipedia tool: {elapsed_time:.2f} seconds")
    print(f"Result: {result[:200]}...")  # Print only the first 200 characters

    assert result is not None, "Wikipedia tool returned no result"
    assert elapsed_time < 5, "Wikipedia tool took too long"

@pytest.mark.benchmark
def test_web_search_benchmark():
    """Benchmark the web search tool."""
    query = "Who lives in Gracie Mansion?"
    topic = "general"
    start_time = time.time()
    result = web_search_tool.invoke({"query": query, "topic": topic})
    end_time = time.time()

    elapsed_time = end_time - start_time
    print(f"Elapsed time for web search tool: {elapsed_time:.2f} seconds")
    print(f"Result: {result}")

    assert result is not None, "Web search tool returned no result"
    assert elapsed_time < 50, "Web search tool took too long"

@pytest.mark.benchmark
def test_wolframalpha_benchmark():
    """Benchmark the Wolfram Alpha tool."""
    query = "What is the population of France?"
    start_time = time.time()
    result = wolframalpha_tool.invoke({"query_input": query})
    end_time = time.time()

    elapsed_time = end_time - start_time
    print(f"Elapsed time for Wolfram Alpha tool: {elapsed_time:.2f} seconds")
    print(f"Result: {result}")

    assert result is not None, "Wolfram Alpha tool returned no result"
    assert elapsed_time < 5, "Wolfram Alpha tool took too long"