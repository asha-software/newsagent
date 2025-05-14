import os
import datetime
import pymysql
import json
import uuid
from typing import Any, Optional, Dict, List, Union, Literal
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from processing import process_query, get_user_tool_params

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


class CustomToolCreate(BaseModel):
    name: str
    description: str = ""
    method: Literal['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
    url_template: str
    headers: Optional[Dict[str, str]] = None
    default_params: Optional[Dict[str, str]] = None
    data: Optional[Dict[str, str]] = None
    json_payload: Optional[Dict[str, str]] = None
    docstring: str = ""
    target_fields: Optional[List[List[Union[str, int]]]] = None
    param_mapping: Dict[str, Dict[str, Union[str, Literal['url_params', 'params', 'headers', 'data', 'json']]]] = Field(...)
    is_active: bool = True
    is_preferred: bool = False


class CustomToolResponse(BaseModel):
    id: int
    name: str
    description: str
    method: str
    url_template: str
    created_at: datetime.datetime
    is_active: bool



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


async def get_cached_result(user_id: int, query: str) -> Optional[dict]:
    """
    Check if a cached result exists for the given user and query using the Django table.
    
    Args:
        user_id: The ID of the user
        query: The query text
        
    Returns:
        The cached result data if found, None otherwise
    """
    try:
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT result_data FROM user_info_sharedsearchresult
                WHERE user_id = %s AND query = %s
                """,
                (user_id, query)
            )
            row = cursor.fetchone()
            if row:
                # The result_data is stored as JSON in the database
                return json.loads(row[0]) if isinstance(row[0], str) else row[0]
        return None
    except Exception as e:
        print(f"Error retrieving cached result: {e}")
        return None
    finally:
        if 'connection' in locals() and connection:
            connection.close()

async def cache_result(user_id: int, query: str, result_data: dict) -> bool:
    """
    Cache a query result for future use in the Django table.
    
    Args:
        user_id: The ID of the user
        query: The query text
        result_data: The result data to cache
        
    Returns:
        True if successful, False otherwise
    """
    try:
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            # Check if a record already exists
            cursor.execute(
                """
                SELECT id FROM user_info_sharedsearchresult
                WHERE user_id = %s AND query = %s
                """,
                (user_id, query)
            )
            existing_record = cursor.fetchone()
            
            if existing_record:
                # Update existing record
                cursor.execute(
                    """
                    UPDATE user_info_sharedsearchresult
                    SET result_data = %s, created_at = NOW()
                    WHERE id = %s
                    """,
                    (json.dumps(result_data), existing_record[0])
                )
            else:
                # Insert new record with UUID as id (using hex format without hyphens)
                cursor.execute(
                    """
                    INSERT INTO user_info_sharedsearchresult
                    (id, user_id, query, result_data, created_at, is_public)
                    VALUES (%s, %s, %s, %s, NOW(), %s)
                    """,
                    (uuid.uuid4().hex, user_id, query, json.dumps(result_data), False)
                )
            
            connection.commit()
        return True
    except Exception as e:
        print(f"Error caching result: {e}")
        return False
    finally:
        if 'connection' in locals() and connection:
            connection.close()

@app.post("/query")
async def query(request: Request, user: dict[str, Any] = Depends(get_current_user)):
    # User is authenticated at this point

    # Parse the request body
    req = await request.json()

    text = req.get('body')

    # Extract the sources array from the request
    tools = req.get('sources')
    print(f"Selected sources: {tools}")

    # Reject the query if tools is not properly formatted (should be a list)
    if tools is not None and not isinstance(tools, list):
        raise HTTPException(
            status_code=400, detail="'sources' must be a list of tool names.")
    
    # If no tools are selected, use the default built-in tools
    if not tools:
        # Get the default built-in tools
        builtin_tools_response = await get_builtin_tools()
        tools = [tool['name'] for tool in builtin_tools_response['tools']]
        print(f"No tools selected, using default tools: {tools}")

    if not text:
        raise HTTPException(
            status_code=400, detail="Input {'body': str} is required.")
    
    if len(text) > 3500:
        raise HTTPException(
            status_code=400,
            detail="Input text exceeds the maximum allowed length of 3500 characters."
        )
    
    # Check for cached result
    cached_result = await get_cached_result(user["id"], text)
    if cached_result:
        print(f"Using cached result for query: {text[:50]}...")
        return cached_result
    
    print(f"No cached result found, processing query: {text[:50]}...")
    user_tool_kwargs = await get_user_tool_params(user["id"], tools) if user else []
    
    print(f"User tool parameters: {user_tool_kwargs}")
    
    verdict_results = await process_query(text, builtin_tools=tools, user_tool_kwargs=user_tool_kwargs)
    
    # Cache the result for future use
    await cache_result(user["id"], text, verdict_results)
    print(f"Cached result for query: {text[:50]}...")
    
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

@app.post("/tools/preferences")
async def set_tool_preferences(request: Request, user: dict[str, Any] = Depends(get_current_user)):
    """
    Endpoint to update tool preferences for a user.
    Tools passed in the request will be marked as preferred, and all others will be unmarked.
    """
    req = await request.json()

    # Extract tool names from the request
    preferred_tool_names = req.get("tools", [])

    # Validate input
    if not isinstance(preferred_tool_names, list):
        raise HTTPException(status_code=400, detail="'tools' must be a list.")

    try:
        # Connect directly to MySQL database
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            # Set is_preferred to True for the specified tools
            if preferred_tool_names:
                cursor.execute(
                    """
                    UPDATE user_info_usertool
                    SET is_preferred = TRUE
                    WHERE user_id = %s AND name IN %s
                    """,
                    [user["id"], tuple(preferred_tool_names)]
                )

            # Set is_preferred to False for all other tools
            cursor.execute(
                """
                UPDATE user_info_usertool
                SET is_preferred = FALSE
                WHERE user_id = %s AND name NOT IN %s
                """,
                [user["id"], tuple(preferred_tool_names)]
            )

            connection.commit()

        return {"message": "Tool preferences updated successfully."}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error updating tool preferences: {str(e)}"
        )
    finally:
        if 'connection' in locals() and connection:
            connection.close()


@app.post("/tools/custom", response_model=CustomToolResponse)
async def create_custom_tool(tool: CustomToolCreate, user: dict[str, Any] = Depends(get_current_user)):
    """
    Creates a new custom tool for the authenticated user.
    This endpoint allows users to define tools programmatically through the API.
    """
    try:
        # Connect directly to MySQL database
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            # Check if a tool with the same name already exists for this user
            cursor.execute(
                """
                SELECT id FROM user_info_usertool 
                WHERE user_id = %s AND name = %s
                """,
                (user["id"], tool.name)
            )
            if cursor.fetchone():
                raise HTTPException(
                    status_code=400,
                    detail=f"A tool with the name '{tool.name}' already exists."
                )

            # Fetch the list of built-in tools
            builtin_tools_response = await get_builtin_tools()
            builtin_tools = [tool['name'] for tool in builtin_tools_response['tools']]

            # Check if the tool name conflicts with built-in tools
            if tool.name in builtin_tools:
                raise HTTPException(
                    status_code=400,
                    detail=f"The tool name '{tool.name}' conflicts with a built-in tool name. Please choose a different name."
                )

            # Insert the new tool
            cursor.execute(
                """
                INSERT INTO user_info_usertool (
                    user_id, name, description, created_at, updated_at, is_active,
                    method, url_template, headers, default_params, data, json_payload,
                    docstring, target_fields, param_mapping, is_preferred
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    user["id"], tool.name, tool.description, datetime.datetime.now(), datetime.datetime.now(),
                    tool.is_active, tool.method, tool.url_template, 
                    json.dumps(tool.headers) if tool.headers else None,
                    json.dumps(tool.default_params) if tool.default_params else None,
                    json.dumps(tool.data) if tool.data else None,
                    json.dumps(tool.json_payload) if tool.json_payload else None,
                    tool.docstring,
                    json.dumps(tool.target_fields) if tool.target_fields else None,
                    json.dumps(tool.param_mapping),
                    tool.is_preferred
                )
            )
            tool_id = cursor.lastrowid
            connection.commit()

            # Get the newly created tool
            cursor.execute(
                """
                SELECT id, name, description, method, url_template, created_at, is_active
                FROM user_info_usertool 
                WHERE id = %s
                """,
                (tool_id,)
            )
            row = cursor.fetchone()

            return {
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "method": row[3],
                "url_template": row[4],
                "created_at": row[5],
                "is_active": bool(row[6])
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error creating custom tool: {str(e)}")
    finally:
        if 'connection' in locals() and connection:
            connection.close()


@app.get("/tools/custom")
async def list_custom_tools(user: dict[str, Any] = Depends(get_current_user)):
    """
    Lists all custom tools for the authenticated user.
    """
    try:
        # Connect directly to MySQL database
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            # Get all custom tools for the user
            cursor.execute(
                """
                SELECT id, name, description, method, url_template, created_at, is_active
                FROM user_info_usertool 
                WHERE user_id = %s
                ORDER BY created_at DESC
                """,
                (user["id"],)
            )
            rows = cursor.fetchall()

            return [
                {
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "method": row[3],
                    "url_template": row[4],
                    "created_at": row[5],
                    "is_active": bool(row[6])
                }
                for row in rows
            ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error listing custom tools: {str(e)}")
    finally:
        if 'connection' in locals() and connection:
            connection.close()


@app.delete("/tools/custom/{tool_id}")
async def delete_custom_tool(tool_id: int, user: dict[str, Any] = Depends(get_current_user)):
    """
    Deletes a custom tool for the authenticated user.
    """
    try:
        # Connect directly to MySQL database
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            # Check if the tool belongs to the user
            cursor.execute(
                """
                SELECT id FROM user_info_usertool 
                WHERE id = %s AND user_id = %s
                """,
                (tool_id, user["id"])
            )
            if not cursor.fetchone():
                raise HTTPException(
                    status_code=404, detail="Custom tool not found")

            # Delete the tool
            cursor.execute(
                "DELETE FROM user_info_usertool WHERE id = %s",
                (tool_id,)
            )
            connection.commit()

            return {"message": "Custom tool deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error deleting custom tool: {str(e)}")
    finally:
        if 'connection' in locals() and connection:
            connection.close()

@app.delete("/cache")
async def clear_cache(user: dict[str, Any] = Depends(get_current_user)):
    """
    Clears all cached queries for the authenticated user.
    """
    try:
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM user_info_sharedsearchresult WHERE user_id = %s",
                (user["id"],)
            )
            connection.commit()
        return {"message": "Cache cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")
    finally:
        if 'connection' in locals() and connection:
            connection.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
