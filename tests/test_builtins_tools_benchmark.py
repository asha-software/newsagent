import pytest
from core.agents.tools.builtins.calculator import tool_function as calculator_tool
from core.agents.tools.builtins.wikipedia import tool_function as wikipedia_tool
from core.agents.tools.builtins.web_search import tool_function as web_search_tool
from core.agents.tools.builtins.wolframalpha import tool_function as wolframalpha_tool

@pytest.mark.benchmark
def test_calculator_benchmark(benchmark):
    """Benchmark the calculator tool."""
    expression = "37593 * 67"

    def calculator_run():
        return calculator_tool.invoke({"expression": expression})

    result = benchmark(calculator_run)
    assert result is not None, "Calculator tool returned no result"

@pytest.mark.benchmark
def test_wikipedia_benchmark(benchmark):
    """Benchmark the wikipedia tool."""
    query = "Apple Podcasts"

    def wikipedia_run():
        return wikipedia_tool.invoke({"query_str": query})

    result = benchmark(wikipedia_run)
    assert result is not None, "Wikipedia tool returned no result"

@pytest.mark.benchmark
def test_web_search_benchmark(benchmark):
    """Benchmark the web search tool."""
    query = "Who lives in Gracie Mansion?"
    topic = "general"

    def web_search_run():
        return web_search_tool.invoke({"query": query, "topic": topic})

    result = benchmark(web_search_run)
    assert result is not None, "Web search tool returned no result"

@pytest.mark.benchmark
def test_wolframalpha_benchmark(benchmark):
    """Benchmark the Wolfram Alpha tool."""
    query = "What is the population of France?"

    def wolframalpha_run():
        return wolframalpha_tool.invoke({"query_input": query})

    result = benchmark(wolframalpha_run)
    assert result is not None, "Wolfram Alpha tool returned no result"