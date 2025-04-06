import pymysql
from typing import Any
from core.middlewares.auth import DB_CONFIG
from core.agents.claim_decomposer import claim_decomposer
from core.agents.research_agent import create_agent as create_research_agent
from core.agents.reasoning_agent import reasoning_agent
from core.agents.verdict_agent import verdict_agent
from core.agents.utils.common_types import Analysis, Evidence


async def get_user_tool_params(user_id: int, tools: list[str]) -> list[dict[str, Any]]:
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


def delete_messages(states: list[dict]):
    for state in states:
        del state['messages']


def create_analyses(claims: list[str], labels: list[str],
                    justifications: list[str], evidence_lists: list[list[Evidence]]) -> list[Analysis]:
    """
    Combine parallel lists into a list of Analysis objects.

    Args:
        claims: List of claim strings
        labels: List of verdict labels (true, false, etc.)
        justifications: List of justification strings
        evidence_lists: List of evidence lists (each inner list contains Evidence objects for one claim)

    Returns:
        List of Analysis objects combining the corresponding elements
    """
    return [
        Analysis(
            claim=claim,
            label=label,
            justification=justification,
            evidence=evidence_list
        )
        for claim, label, justification, evidence_list in zip(claims, labels, justifications, evidence_lists)
    ]


async def process_query(text: str, builtin_tools: list, user_tool_kwargs: list = []) -> dict:

    # Try constructing research agent
    research_agent = create_research_agent(
        model="mistral-nemo",
        builtin_tools=builtin_tools,
        user_tool_kwargs=user_tool_kwargs,
    )

    # Claims decomposer
    initial_state = {"text": text}
    result = claim_decomposer.invoke(
        initial_state,
        config={"run_name": "claim_decomposer", }
    )
    claims = result["claims"]

    research_results = [research_agent.invoke(
        {"claim": claim},
        config={"run_name": "research_agent"}
    ) for claim in claims]
    delete_messages(research_results)

    reasoning_results = [reasoning_agent.invoke(
        state,
        config={"run_name": "reasoning_agent"}
    ) for state in research_results]
    delete_messages(reasoning_results)

    # Process reasoning results with verdict_agent
    verdict_results = verdict_agent.invoke({
        "claims": claims,
        "labels": [r["label"] for r in reasoning_results],
        "justifications": [r["justification"] for r in reasoning_results],
        "messages": []
    }, config={"run_name": "verdict_agent"})

    # Clean up messages in verdict_results
    delete_messages([verdict_results])
    verdict_results['evidence'] = [res['evidence'] for res in research_results]
    verdict_results['claims'] = claims

    analyses = create_analyses(verdict_results['claims'], verdict_results['labels'],
                               verdict_results['justifications'], verdict_results['evidence'])

    results = {
        "final_label": verdict_results['final_label'],
        "final_justification": verdict_results['final_justification'],
        "analyses": analyses,
    }
    return results


def main():
    # Example usage
    text = "Python was created by Guido van Rossum"
    selected_sources = []

    import asyncio
    result = asyncio.run(process_query(text, selected_sources))
    print(result)


if __name__ == "__main__":
    main()
