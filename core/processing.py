from core.middlewares.auth import DB_CONFIG
import pymysql, typing
from core.pipeline import pipeline

async def get_user_tool_params(user_id: int, tools: list[str]) -> list[dict[str, typing.Any]]:
    """
    Retrieves user-defined tool parameters from the database.
    
    Args:
        user_id: The ID of the user
        tools: List of tool names to retrieve
        
    Returns:
        A list of dictionaries containing tool parameters for create_tool
    """
    user_tool_params = []
    
    if not user_id:
        return user_tool_params
        
    try:
        # Connect directly to MySQL database
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            # Get all active user tools for this user that match the selected tools
            placeholders = ', '.join(['%s'] * len(tools))
            cursor.execute(
                f"""
                SELECT name, description, method, url_template, headers, default_params, 
                       data, json_payload, docstring, target_fields, param_mapping, is_preferred
                FROM user_info_usertool 
                WHERE user_id = %s AND name IN ({placeholders}) AND is_active = 1
                """,
                (user_id, *tools)
            )
            rows = cursor.fetchall()
            
            # Store the parameters for each user tool
            for row in rows:
                user_tool_params.append({
                    'name': row[0],
                    'description': row[1],
                    'method': row[2],
                    'url_template': row[3],
                    'headers': row[4],
                    'default_params': row[5],
                    'data': row[6],
                    'json_payload': row[7],
                    'docstring': row[8],
                    'target_fields': row[9],
                    'param_mapping': row[10],
                    'is_preferred': bool(row[11])
                })
    except Exception as e:
        print(f"Error retrieving user tool parameters: {e}")
    finally:
        if 'connection' in locals() and connection:
            connection.close()
            
    return user_tool_params

# new lightweight wrapper (signature unchanged for app.py)
async def process_query(text: str, builtin_tools: list, user_tool_kwargs: list = []):
    state = {"text": text}
    result = pipeline.invoke(state)
    return result
