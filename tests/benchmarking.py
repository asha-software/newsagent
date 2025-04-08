import pytest
import time
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from starlette.responses import JSONResponse
from core.app import app

client = TestClient(app)

@pytest.mark.benchmark
def test_query_benchmark():
    """Benchmark the /query endpoint."""
    payload = {
        "body": "What is the capital of France?",
        "sources": ["web_search", "wikipedia"]
    }

    # Patch the APIKeyMiddleware and RateLimitMiddleware to bypass them
    with patch("core.middlewares.auth.APIKeyMiddleware.__call__", new_callable=AsyncMock) as mock_auth_middleware, \
         patch("core.middlewares.rate_limit.RateLimitMiddleware.dispatch", new_callable=AsyncMock) as mock_rate_limit_middleware:
        mock_auth_middleware.return_value = None
        mock_rate_limit_middleware.return_value = JSONResponse(content={"message": "Rate limit bypassed"})

        start_time = time.time()
        response = client.post("/query", json=payload)
        end_time = time.time()

        elapsed_time = end_time - start_time
        print(f"Elapsed time for /query: {elapsed_time:.2f} seconds")

        assert response.status_code == 200, "Query endpoint failed"
        assert elapsed_time < 5, "Query endpoint took too long"