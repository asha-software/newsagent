from core.agents.claim_decomposer import claim_decomposer
from core.agents.research_agent import create_agent as create_research_agent
from core.agents.reasoning_agent import reasoning_agent
from core.agents.verdict_agent import verdict_agent


def delete_messages(states: list[dict]):
    for state in states:
        del state['messages']


async def process_query(text: str, selected_sources: list) -> dict:
    # TODO: selected_sources needs to be passed to the research agent to resolve which tools to bind
    # Try constructing research agent
    research_agent = create_research_agent(
        model="mistral-nemo",
        builtin_tools={
            'calculator': ['multiply', 'add'],
            'wikipedia_tool': ['query'],
            'web_search': ['web_search_tavily'],
        },
        user_tool_kwargs=[]
    )

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

    # Process reasoning results with verdict_agent
    verdict_results = verdict_agent.invoke({
        "claims": claims,
        "labels": [r["label"] for r in reasoning_results],
        "justifications": [r["justification"] for r in reasoning_results],
        "messages": []
    })

    # Clean up messages in verdict_results
    delete_messages([verdict_results])
    return verdict_results


def main():
    # Example usage
    text = "Python was created by Guido van Rossum"
    selected_sources = []

    import asyncio
    result = asyncio.run(process_query(text, selected_sources))
    print(result)


if __name__ == "__main__":
    main()
