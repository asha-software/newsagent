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
    tools = [
        {"name": "calculator", "display_name": "Calculator"},
        {"name": "wikipedia", "display_name": "Wikipedia"},
        {"name": "web_search", "display_name": "Web Search"},
        {"name": "wolframalpha", "display_name": "Wolfram Alpha"}
    ]
    
    return {"tools": tools}


async def get_user_preferred_tools(user_id: int) -> list[str]:
    """
    Returns a list of preferred custom tool names for the user.
    If the user has no preferred custom tools, returns an empty list.
    This function only returns custom tools, not built-in tools.
    """
    preferred_tools = []
    
    if not user_id:
        return preferred_tools
        
    try:
        # Connect directly to MySQL database
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            # Get all active preferred custom tools for this user
            # Exclude built-in tools by checking for non-empty url_template
            cursor.execute(
                """
                SELECT name
                FROM user_info_usertool 
                WHERE user_id = %s AND is_active = 1 AND is_preferred = 1
                AND url_template != ''
                """,
                (user_id,)
            )
            rows = cursor.fetchall()
            
            # Extract tool names
            preferred_tools = [row[0] for row in rows]
            
    except Exception as e:
        print(f"Error retrieving user preferred tools: {e}")
    finally:
        if 'connection' in locals() and connection:
            connection.close()
            
    return preferred_tools

async def check_cached_query(user_id: int, query_text: str) -> Optional[Dict[str, Any]]:
    """
    Check if a query has been cached for the user.
    Returns the cached result if found, None otherwise.
    """
    try:
        # Connect directly to MySQL database
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            # Check if the query exists in the cache
            cursor.execute(
                """
                SELECT id, query, result_data, created_at, is_public
                FROM user_info_sharedsearchresult
                WHERE user_id = %s AND query = %s
                """,
                (user_id, query_text)
            )
            row = cursor.fetchone()
            
            if row:
                return {
                    "id": row[0],
                    "query": row[1],
                    "result_data": json.loads(row[2]),
                    "created_at": row[3],
                    "is_public": bool(row[4])
                }
            return None
    except Exception as e:
        print(f"Error checking cached query: {e}")
        return None
    finally:
        if 'connection' in locals() and connection:
            connection.close()

async def save_query_result(user_id: int, query_text: str, result_data: Dict[str, Any], is_public: bool = False) -> Dict[str, Any]:
    """
    Save a query result to the cache.
    Returns the saved result.
    """
    try:
        # Connect directly to MySQL database
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            # Check if the query already exists
            cursor.execute(
                """
                SELECT id FROM user_info_sharedsearchresult
                WHERE user_id = %s AND query = %s
                """,
                (user_id, query_text)
            )
            existing_row = cursor.fetchone()
            
            if existing_row:
                # Update the existing record
                cursor.execute(
                    """
                    UPDATE user_info_sharedsearchresult
                    SET result_data = %s, is_public = %s
                    WHERE id = %s
                    """,
                    (json.dumps(result_data), is_public, existing_row[0])
                )
                result_id = existing_row[0]
            else:
                # Create a new record
                result_id = uuid.uuid4().hex
                cursor.execute(
                    """
                    INSERT INTO user_info_sharedsearchresult
                    (id, user_id, query, result_data, created_at, is_public)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (result_id, user_id, query_text, json.dumps(result_data), datetime.datetime.now(), is_public)
                )
            
            connection.commit()
            
            return {
                "id": result_id,
                "query": query_text,
                "result_data": result_data,
                "is_public": is_public
            }
    except Exception as e:
        print(f"Error saving query result: {e}")
        return None
    finally:
        if 'connection' in locals() and connection:
            connection.close()

@app.post("/query")
async def query(request: Request, user: dict[str, Any] = Depends(get_current_user)):
    # User is authenticated at this point

    # Parse the request body
    try:
        req = await request.json()
    except json.JSONDecodeError:
        # Handle case where request body is not valid JSON
        raise HTTPException(
            status_code=400, detail="Invalid JSON in request body")

    text = req.get('body')

    # Extract the sources array from the request
    tools = req.get('sources', req.get('source', []))  # Default to empty list if not provided
    
    # Convert to list if a single string was provided
    if isinstance(tools, str):
        tools = [tools]
        
    print(f"Selected sources: {tools}")

    # Reject the query if tools is not properly formatted (should be a list)
    if tools is not None and not isinstance(tools, list):
        raise HTTPException(
            status_code=400, detail="'sources' must be a list of tool names.")
    
    # If no tools are selected, use the user's preferred tools if available,
    # otherwise use the default built-in tools
    print(f"DEBUG: Initial tools value: {tools}")
    print(f"DEBUG: User ID: {user['id']}")
    
    if not tools:
        print("DEBUG: No tools selected, checking for preferred tools")
        # Get the user's preferred tools
        preferred_tools = await get_user_preferred_tools(user["id"])
        print(f"DEBUG: Preferred tools found: {preferred_tools}")
        
        if preferred_tools:
            tools = preferred_tools
            print(f"DEBUG: Using user's preferred tools: {tools}")
        else:
            # If user has no preferred tools, fall back to default built-in tools
            print("DEBUG: No preferred tools found, falling back to default tools")
            builtin_tools_response = await get_builtin_tools()
            tools = [tool['name'] for tool in builtin_tools_response['tools']]
            print(f"DEBUG: Using default built-in tools: {tools}")

    if not text:
        raise HTTPException(
            status_code=400, detail="Input {'body': str} is required.")
    
    if len(text) > 3500:
        raise HTTPException(
            status_code=400,
            detail="Input text exceeds the maximum allowed length of 3500 characters."
        )
    
    # Check if the query is already cached
    cached_result = await check_cached_query(user["id"], text)
    if cached_result:
        print(f"Using cached result for query: {text[:50]}...")
        return cached_result["result_data"]
    
    # If not cached, process the query
    user_tool_kwargs = await get_user_tool_params(user["id"], tools) if user else []
    
    print(f"User tool parameters: {user_tool_kwargs}")
    
    verdict_results = await process_query(text, builtin_tools=tools, user_tool_kwargs=user_tool_kwargs)
    
    # Save the result for future use
    await save_query_result(user["id"], text, verdict_results)
    
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

# Add a new endpoint to check for cached queries
@app.get("/cached-queries")
async def get_cached_queries(user: dict[str, Any] = Depends(get_current_user)):
    """
    Returns a list of cached queries for the authenticated user.
    """
    try:
        # Connect directly to MySQL database
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            # Get all cached queries for the user
            cursor.execute(
                """
                SELECT id, query, created_at, is_public
                FROM user_info_sharedsearchresult
                WHERE user_id = %s
                ORDER BY created_at DESC
                """,
                (user["id"],)
            )
            rows = cursor.fetchall()

            return [
                {
                    "id": row[0],
                    "query": row[1],
                    "created_at": row[2],
                    "is_public": bool(row[3])
                }
                for row in rows
            ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error listing cached queries: {str(e)}")
    finally:
        if 'connection' in locals() and connection:
            connection.close()

# Add an endpoint to get a specific cached query
@app.get("/cached-queries/{query_id}")
async def get_cached_query(query_id: str, user: dict[str, Any] = Depends(get_current_user)):
    """
    Returns a specific cached query for the authenticated user.
    """
    try:
        # Connect directly to MySQL database
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            # Get the cached query
            cursor.execute(
                """
                SELECT id, query, result_data, created_at, is_public
                FROM user_info_sharedsearchresult
                WHERE id = %s AND (user_id = %s OR is_public = 1)
                """,
                (query_id, user["id"])
            )
            row = cursor.fetchone()

            if not row:
                raise HTTPException(
                    status_code=404, detail="Cached query not found or not accessible")

            return {
                "id": row[0],
                "query": row[1],
                "result_data": json.loads(row[2]),
                "created_at": row[3],
                "is_public": bool(row[4])
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving cached query: {str(e)}")
    finally:
        if 'connection' in locals() and connection:
            connection.close()

# Add an endpoint to delete a cached query
@app.delete("/cached-queries/{query_id}")
async def delete_cached_query(query_id: str, user: dict[str, Any] = Depends(get_current_user)):
    """
    Deletes a cached query for the authenticated user.
    """
    try:
        # Connect directly to MySQL database
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            # Check if the cached query belongs to the user
            cursor.execute(
                """
                SELECT id FROM user_info_sharedsearchresult
                WHERE id = %s AND user_id = %s
                """,
                (query_id, user["id"])
            )
            if not cursor.fetchone():
                raise HTTPException(
                    status_code=404, detail="Cached query not found")

            # Delete the cached query
            cursor.execute(
                "DELETE FROM user_info_sharedsearchresult WHERE id = %s",
                (query_id,)
            )
            connection.commit()

            return {"message": "Cached query deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error deleting cached query: {str(e)}")
    finally:
        if 'connection' in locals() and connection:
            connection.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
