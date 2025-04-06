"""
Rate limiting middleware for the FastAPI application.

This module contains middleware for implementing rate limiting on API endpoints.
"""
import time
from collections import defaultdict
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for implementing rate limiting.

    This middleware tracks API requests and limits them based on a configurable
    number of requests per minute per API key.
    """

    def __init__(self, app, requests_per_minute=20):
        """
        Initialize the rate limit middleware.

        Args:
            app: The FastAPI application
            requests_per_minute: Maximum number of requests allowed per minute
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_history = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        """
        Process the request and apply rate limiting.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            The response, potentially with rate limit headers or a 429 status code
        """
        # Skip rate limiting for non-query endpoints
        if not request.url.path.endswith('/query'):
            return await call_next(request)

        # Get the API key from the header
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return await call_next(request)

        # Check rate limit
        current_time = time.time()
        # Remove requests older than 1 minute
        self.request_history[api_key] = [
            timestamp for timestamp in self.request_history[api_key]
            if current_time - timestamp < 60
        ]

        # Check if the user has exceeded the rate limit
        if len(self.request_history[api_key]) >= self.requests_per_minute:
            # Calculate time until reset
            oldest_request = self.request_history[api_key][0]
            seconds_until_reset = 60 - (current_time - oldest_request)

            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"Rate limit exceeded. Try again in {int(seconds_until_reset)} seconds.",
                    "rate_limit": {
                        "limit": self.requests_per_minute,
                        "remaining": 0,
                        "reset_after_seconds": int(seconds_until_reset)
                    }
                }
            )

        # Add the current request to the history
        self.request_history[api_key].append(current_time)

        # Add rate limit headers to the response
        response = await call_next(request)
        response.headers["X-Rate-Limit-Limit"] = str(self.requests_per_minute)
        response.headers["X-Rate-Limit-Remaining"] = str(
            self.requests_per_minute - len(self.request_history[api_key]))

        return response
