"""
Authentication middleware for the FastAPI application.

This module contains middleware for handling API key authentication.
"""
import os
import pymysql
from typing import Optional, Dict, Any
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# Database connection settings - directly configured without Django dependency
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "fakenews_user"),
    "password": os.getenv("DB_PASSWORD", "password"),
    "database": os.getenv("DB_NAME", "fakenews_db"),
    "port": int(os.getenv("DB_PORT", "3306")),
}


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Middleware for API key authentication.
    
    This middleware extracts the API key from the request header,
    validates it against the database, and attaches the user to the request state.
    """
    async def dispatch(self, request: Request, call_next):
        # Get the API key from the header
        api_key = request.headers.get("X-API-Key")
        request.state.user = None

        if api_key:
            # Get the user from the API key
            user = await self.get_user_from_api_key(api_key)
            if user:
                request.state.user = user

        response = await call_next(request)
        return response

    async def get_user_from_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Get the user associated with the API key.
        
        Args:
            api_key: The API key to validate
            
        Returns:
            A dictionary containing user information if the API key is valid,
            None otherwise.
        """
        try:
            # Connect directly to MySQL database
            connection = pymysql.connect(**DB_CONFIG)
            with connection.cursor() as cursor:
                # Get the user associated with the API key
                cursor.execute(
                    """
                    SELECT au.id, au.username, au.email 
                    FROM auth_user au
                    JOIN user_info_apikey uak ON uak.user_id = au.id
                    WHERE uak.key = %s AND uak.is_active = 1
                    """,
                    (api_key,)
                )
                user_row = cursor.fetchone()

                if user_row:
                    return {
                        "id": user_row[0],
                        "username": user_row[1],
                        "email": user_row[2]
                    }

                return None
        except Exception as e:
            print(f"Error getting user from API key: {e}")
            return None
        finally:
            if 'connection' in locals() and connection:
                connection.close()
