import pytest
import time
from unittest.mock import AsyncMock, patch
from core.processing import process_query
import asyncio

@pytest.mark.asyncio
@pytest.mark.benchmark
async def test_process_query_benchmark():
    """Benchmark the core logic of the process_query function."""
    text = "The capital of France is Paris."
    tools = ["web_search","wikipedia"]

    # Mock external dependencies
    with patch("core.processing.get_user_tool_params", new_callable=AsyncMock) as mock_get_user_tool_params:
        mock_get_user_tool_params.return_value = []

        start_time = time.time()
        verdict_results = await process_query(text, builtin_tools=[], user_tool_kwargs=[])
        end_time = time.time()

        elapsed_time = end_time - start_time
        print(f"Elapsed time for process_query: {elapsed_time:.2f} seconds")
        print(f"Verdict results: {verdict_results}")

        assert verdict_results is not None, "process_query returned no results"
        assert "final_label" in verdict_results, "process_query did not return final_label"
        assert elapsed_time < 500, "process_query took too long"
