from core.agents.claim_decomposer import claim_decomposer
from core.agents.research_agent import create_agent as create_research_agent
from core.agents.reasoning_agent import reasoning_agent
from core.agents.verdict_agent import verdict_agent
from core.agents.utils.common_types import Analysis, Evidence


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
        # TODO: take this from user preferences
        builtin_tools=['wikipedia', 'web_search'],
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
