import os
import sys
import base64
import datetime
import pymysql
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Request, Depends
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware
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
    from django.contrib.sessions.serializers import JSONSerializer
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

# Django session authentication middleware
class DjangoSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Get the session ID from the cookie
        session_id = request.cookies.get("sessionid")
        request.state.user = None
        
        if session_id:
            # Get the user from the session
            user = await self.get_user_from_session(session_id)
            if user:
                request.state.user = user
        
        response = await call_next(request)
        return response
    
    async def get_user_from_session(self, session_key: str) -> Optional[Dict[str, Any]]:
        try:
            # Connect to the Django database
            connection = pymysql.connect(**DB_CONFIG)
            with connection.cursor() as cursor:
                # Get the session from the database
                cursor.execute(
                    "SELECT session_data, expire_date FROM django_session WHERE session_key = %s",
                    (session_key,)
                )
                session_row = cursor.fetchone()
                
                if not session_row or session_row[1] < datetime.datetime.now():
                    return None
                
                # Get the user ID from the session data
                session_data = session_row[0] 
                
                try:
                    # Remove the base64 padding
                    session_data = session_data.decode('ascii')
                    if ':' in session_data:
                        session_data = session_data.split(':', 1)[1]
                    
                    # Decode the base64 data
                    decoded = base64.b64decode(session_data).decode('utf-8')
                    
                    # Parse the JSON data
                    session_dict = JSONSerializer().loads(decoded)
                    
                    # Get the user ID from the session
                    auth_user_id = session_dict.get('_auth_user_id')
                    
                    if not auth_user_id:
                        return None
                    
                    # Get the user from the database
                    cursor.execute(
                        "SELECT id, username, email FROM auth_user WHERE id = %s",
                        (auth_user_id,)
                    )
                    user_row = cursor.fetchone()
                except Exception:
                    # Fallback to the JOIN query if decoding fails
                    cursor.execute(
                        """
                        SELECT au.id, au.username, au.email 
                        FROM auth_user au
                        JOIN django_session ds ON ds.session_key = %s
                        WHERE ds.expire_date > NOW()
                        LIMIT 1
                        """,
                        (session_key,)
                    )
                    user_row = cursor.fetchone()
                
                if user_row:
                    return {
                        "id": user_row[0],
                        "username": user_row[1],
                        "email": user_row[2]
                    }
                
                return None
        except Exception:
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

# Add the Django session middleware
app.add_middleware(DjangoSessionMiddleware)

# Helper function to get the current user
async def get_current_user(request: Request) -> Dict[str, Any]:
    user = request.state.user
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
