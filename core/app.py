import os
import datetime
import pymysql
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Request, Depends, Header
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
# from agents.claim_decomposer import claim_decomposer
# from agents.research_agent import create_agent as create_research_agent
# from agents.reasoning_agent import reasoning_agent
from processing import process_query

# Database connection settings - directly configured without Django dependency
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "fakenews_user"),
    "password": os.getenv("DB_PASSWORD", "password"),
    "database": os.getenv("DB_NAME", "fakenews_db"),
    "port": int(os.getenv("DB_PORT", "3306")),
}

# API Key authentication middleware


class APIKeyMiddleware(BaseHTTPMiddleware):
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
        try:
            # Connect directly to MySQL database
            connection = pymysql.connect(**DB_CONFIG)
            with connection.cursor() as cursor:
                # Get the user associated with the API key
                # Same query as before, just with a clearer comment
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

# Helper function to get the current user


async def get_current_user(request: Request) -> Dict[str, Any]:
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


@app.post("/query")
async def query(request: Request, user: Dict[str, Any] = Depends(get_current_user)):
    # User is authenticated at this point

    # Parse the request body
    req = await request.json()

    text = req.get('body')

    # Extract the sources array from the request
    # Default to empty list if not provided
    selected_sources = req.get('sources', [])
    print(f"Selected sources: {selected_sources}")

    if not text:
        raise HTTPException(
            status_code=400, detail="Input {'body': str} is required.")

    # Try constructing research agent
    # research_agent = create_research_agent(
    #     model="mistral-nemo",
    #     builtin_tools={
    #         'calculator': ['multiply', 'add'],
    #         'wikipedia': ['query']
    #     },
    #     user_tool_kwargs=[]
    # )

    # # Claims decomposer
    # initial_state = {"text": text}
    # result = claim_decomposer.invoke(initial_state)
    # claims = result["claims"]

    # research_results = [research_agent.invoke(
    #     {"claim": claim, "selected_sources": selected_sources}) for claim in claims]
    # delete_messages(research_results)

    # reasoning_results = [reasoning_agent.invoke(
    #     state) for state in research_results]
    # delete_messages(reasoning_results)

    # return reasoning_results

    reasoning_results = await process_query(text, selected_sources)
    return reasoning_results


@app.get("/user")
async def get_user(user: Dict[str, Any] = Depends(get_current_user)):
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
async def create_api_key(api_key: APIKeyCreate, user: Dict[str, Any] = Depends(get_current_user)):
    """
    Creates a new API key for the authenticated user.
    """
    try:
        # Connect directly to MySQL database
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
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
async def list_api_keys(user: Dict[str, Any] = Depends(get_current_user)):
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
async def delete_api_key(api_key_id: int, user: Dict[str, Any] = Depends(get_current_user)):
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
