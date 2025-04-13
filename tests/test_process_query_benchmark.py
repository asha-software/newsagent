# Note to developers: This benchmark specifically evaluates the agents using the 'mistral-nemo' model.
# Using models of different sizes or configurations may yield significantly different results.

import pytest
from unittest.mock import AsyncMock, patch
from core.processing import process_query
import asyncio

# Refactored to handle the running event loop issue with asyncio.create_task
@pytest.mark.asyncio
@pytest.mark.benchmark
async def test_process_query_benchmark(benchmark):
    """Benchmark the core logic of the process_query function."""
    text = "The capital of France is Paris."

    async def process_query_run():
        with patch("core.processing.get_user_tool_params", new_callable=AsyncMock) as mock_get_user_tool_params:
            mock_get_user_tool_params.return_value = []
            return await process_query(text, builtin_tools=["wikipedia"], user_tool_kwargs=[])

    # Use asyncio.create_task to handle the asynchronous function
    def wrapper():
        return asyncio.create_task(process_query_run())

    result = await benchmark(wrapper)
    assert result is not None, "process_query returned no results"
    assert "final_label" in result, "process_query did not return final_label"
