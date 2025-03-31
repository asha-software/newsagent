import os
import sys
import datetime
import pymysql
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Request, Depends, Header
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
from agents.claim_decomposer import claim_decomposer
from agents.research_agent import research_agent
from agents.reasoning_agent import reasoning_agent

# Add the Django project directory to the Python path
django_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../django'))
sys.path.insert(0, django_path)

# Initialize Django settings for using Django components
try:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'user_query_app.settings')
    import django
    django.setup()
except ImportError as e:
    pass

# Django database connection settings
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "fakenews_user"),
    "password": os.getenv("DB_PASSWORD", "password"),
    "database": os.getenv("DB_NAME", "fakenews_db"),
    "port": 3306,
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
                # Update last_used_at timestamp
                await self.update_api_key_usage(api_key)
        
        response = await call_next(request)
        return response
    
    async def get_user_from_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        try:
            # Connect to the Django database
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
    
    async def update_api_key_usage(self, api_key: str):
        try:
            # Connect to the Django database
            connection = pymysql.connect(**DB_CONFIG)
            with connection.cursor() as cursor:
                # Update the last_used_at timestamp
                cursor.execute(
                    "UPDATE user_info_apikey SET last_used_at = NOW() WHERE key = %s",
                    (api_key,)
                )
                connection.commit()
        except Exception as e:
            print(f"Error updating API key usage: {e}")
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
async def query(request: Request):
    try:
        # Get user information
        user = await get_current_user(request)
        
        # Parse the request body
        req = await request.json()
        text = req.get('body')

        if not text:
            raise HTTPException(
                status_code=400, detail="Input {'body': str} is required.")


        try:
            # Claims decomposer
            initial_state = {"text": text}
            result = claim_decomposer.invoke(initial_state)
            claims = result["claims"]

            research_results = [research_agent.invoke(
                {"claim": claim}) for claim in claims]
            delete_messages(research_results)

            reasoning_results = [reasoning_agent.invoke(
                state) for state in research_results]
            delete_messages(reasoning_results)


            # Add user information to the response
            for result in reasoning_results:
                result["user"] = user["username"]

            return reasoning_results
        except Exception as e:
            # Return a simplified response for debugging
            return {
                "error": "Error processing query",
                "message": str(e),
                "user": user["username"]
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

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


# create_api_key endpoint removed to prevent users from creating unlimited API keys
# API keys should now be created only through the Django admin interface or
# automatically when using the web interface

@app.get("/api-keys")
async def list_api_keys(user: Dict[str, Any] = Depends(get_current_user)):
    """
    Lists all API keys for the authenticated user.
    """
    try:
        # Connect to the Django database
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            # Get all API keys for the user
            cursor.execute(
                """
                SELECT id, name, key, created_at, last_used_at, is_active 
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
        raise HTTPException(status_code=500, detail=f"Error listing API keys: {str(e)}")
    finally:
        if 'connection' in locals() and connection:
            connection.close()

@app.delete("/api-keys/{api_key_id}")
async def delete_api_key(api_key_id: int, user: Dict[str, Any] = Depends(get_current_user)):
    """
    Deletes an API key for the authenticated user.
    """
    try:
        # Connect to the Django database
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
                raise HTTPException(status_code=404, detail="API key not found")
            
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
        raise HTTPException(status_code=500, detail=f"Error deleting API key: {str(e)}")
    finally:
        if 'connection' in locals() and connection:
            connection.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
