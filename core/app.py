import os
import datetime
import pymysql
from typing import Any, Optional
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from processing import process_query

# Import middlewares from the new location
from core.middlewares.auth import APIKeyMiddleware, DB_CONFIG
from core.middlewares.rate_limit import RateLimitMiddleware

# Create FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Add the API key middleware
app.add_middleware(APIKeyMiddleware)
# Add the rate limit middleware
app.add_middleware(RateLimitMiddleware)

# Helper function to get the current user


async def get_current_user(request: Request) -> dict[str, Any]:
    user = request.state.user
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

# API Key models


class APIKeyCreate(BaseModel):
    name: str


class APIKeyResponse(BaseModel):
    id: int
    name: str
    key: str
    created_at: datetime.datetime
    last_used_at: Optional[datetime.datetime] = None
    is_active: bool


def delete_messages(states: list[dict]):
    for state in states:
        del state['messages']


@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/tools/builtins")
async def get_builtin_tools():
    """
    Returns a list of available built-in tools.
    This endpoint is used by the Django container to get the list of built-in tools.
    """
    # Hardcoded list of built-in tools
    # This is a simpler approach that ensures all tools are included
    tools = [
        {"name": "calculator", "display_name": "Calculator"},
        {"name": "wikipedia", "display_name": "Wikipedia"},
        {"name": "web_search", "display_name": "Web Search"},
        {"name": "wolframalpha", "display_name": "Wolfram Alpha"}
    ]
    
    return {"tools": tools}


@app.post("/query")
async def query(request: Request, user: dict[str, Any] = Depends(get_current_user)):
    # User is authenticated at this point

    # Parse the request body
    req = await request.json()

    text = req.get('body')

    # Extract the sources array from the request
    tools = req.get('sources')
    print(f"Selected sources: {tools}")

    # Convert string to list if needed
    if isinstance(tools, str):
        tools = [tools]
    
    # If no tools are selected, use the default built-in tools
    if not tools:
        # Get the default built-in tools
        builtin_tools_response = await get_builtin_tools()
        tools = [tool['name'] for tool in builtin_tools_response['tools']]
        print(f"No tools selected, using default tools: {tools}")

    if not text:
        raise HTTPException(
            status_code=400, detail="Input {'body': str} is required.")
    
    # Get user-defined tools if the user is authenticated
    from processing import get_user_tool_params
    
    user_tool_kwargs = await get_user_tool_params(user["id"], tools) if user else []
    
    print(f"User tool parameters: {user_tool_kwargs}")
    
    verdict_results = await process_query(text, builtin_tools=tools, user_tool_kwargs=user_tool_kwargs)
    return verdict_results


@app.get("/user")
async def get_user(user: dict[str, Any] = Depends(get_current_user)):
    """
    Returns information about the authenticated user.
    This endpoint can be used to test if authentication is working.
    """
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"]
    }


@app.post("/api-keys")
async def create_api_key(api_key: APIKeyCreate, user: dict[str, Any] = Depends(get_current_user)):
    """
    Creates a new API key for the authenticated user.
    Limited to 3 API keys per user.
    """
    try:
        # Connect directly to MySQL database
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            # Check if the user already has 3 or more API keys
            cursor.execute(
                """
                SELECT COUNT(*) FROM user_info_apikey 
                WHERE user_id = %s
                """,
                (user["id"],)
            )
            key_count = cursor.fetchone()[0]

            if key_count >= 3:
                raise HTTPException(
                    status_code=400,
                    detail="You can only have a maximum of 3 API keys per account."
                )

            # Generate a new API key
            import uuid
            key = uuid.uuid4().hex

            # Insert the new API key
            cursor.execute(
                """
                INSERT INTO user_info_apikey (user_id, name, `key`, created_at, is_active) 
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user["id"], api_key.name, key, datetime.datetime.now(), True)
            )
            api_key_id = cursor.lastrowid
            connection.commit()

            # Get the newly created API key
            cursor.execute(
                """
                SELECT id, name, `key`, created_at, last_used_at, is_active 
                FROM user_info_apikey 
                WHERE id = %s
                """,
                (api_key_id,)
            )
            row = cursor.fetchone()

            return {
                "id": row[0],
                "name": row[1],
                "key": row[2],
                "created_at": row[3],
                "last_used_at": row[4],
                "is_active": bool(row[5])
            }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error creating API key: {str(e)}")
    finally:
        if 'connection' in locals() and connection:
            connection.close()


@app.get("/api-keys")
async def list_api_keys(user: dict[str, Any] = Depends(get_current_user)):
    """
    Lists all API keys for the authenticated user.
    """
    try:
        # Connect directly to MySQL database
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            # Get all API keys for the user
            cursor.execute(
                """
                SELECT id, name, `key`, created_at, last_used_at, is_active 
                FROM user_info_apikey 
                WHERE user_id = %s
                """,
                (user["id"],)
            )
            rows = cursor.fetchall()

            return [
                {
                    "id": row[0],
                    "name": row[1],
                    "key": row[2],
                    "created_at": row[3],
                    "last_used_at": row[4],
                    "is_active": bool(row[5])
                }
                for row in rows
            ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error listing API keys: {str(e)}")
    finally:
        if 'connection' in locals() and connection:
            connection.close()


@app.delete("/api-keys/{api_key_id}")
async def delete_api_key(api_key_id: int, user: dict[str, Any] = Depends(get_current_user)):
    """
    Deletes an API key for the authenticated user.
    """
    try:
        # Connect directly to MySQL database
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            # Check if the API key belongs to the user
            cursor.execute(
                """
                SELECT id FROM user_info_apikey 
                WHERE id = %s AND user_id = %s
                """,
                (api_key_id, user["id"])
            )
            if not cursor.fetchone():
                raise HTTPException(
                    status_code=404, detail="API key not found")

            # Delete the API key
            cursor.execute(
                "DELETE FROM user_info_apikey WHERE id = %s",
                (api_key_id,)
            )
            connection.commit()

            return {"message": "API key deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error deleting API key: {str(e)}")
    finally:
        if 'connection' in locals() and connection:
            connection.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
