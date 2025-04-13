import pytest
from core.agents.claim_decomposer import claim_decomposer
from core.agents.research_agent import create_agent
from core.agents.reasoning_agent import reasoning_agent
from core.agents.verdict_agent import verdict_agent

@pytest.mark.benchmark
def test_claim_decomposer_benchmark(benchmark):
    """Benchmark the claim decomposer agent."""
    initial_state = {"text": "The sky is blue and the grass is green."}

    def claim_decomposer_run():
        return claim_decomposer.invoke(initial_state)

    result = benchmark(claim_decomposer_run)
    assert result is not None, "Claim decomposer returned no result"

@pytest.mark.benchmark
def test_research_agent_benchmark(benchmark):
    """Benchmark the research agent."""
    builtin_tools_wanted = ['wikipedia', 'web_search']
    research_agent = create_agent(model='mistral-nemo', builtin_tools=builtin_tools_wanted)

    initial_state = {"claim": "Python was created by Guido van Rossum"}

    def research_agent_run():
        return research_agent.invoke(initial_state)

    result = benchmark(research_agent_run)
    assert result is not None, "Research agent returned no result"

@pytest.mark.benchmark
def test_reasoning_agent_benchmark(benchmark):
    """Benchmark the reasoning agent."""
    initial_state = {
        "messages": [],
        "claim": "The Eiffel Tower is in Paris.",
        "evidence": [
            {"name": "Wikipedia", "result": "The Eiffel Tower is located in Paris, France."}
        ],
        "label": None,
        "justification": None
    }

    def reasoning_agent_run():
        return reasoning_agent.invoke(initial_state)

    result = benchmark(reasoning_agent_run)
    assert result is not None, "Reasoning agent returned no result"

@pytest.mark.benchmark
def test_verdict_agent_benchmark(benchmark):
    """Benchmark the verdict agent."""
    initial_state = {
        "messages": [],
        "claims": ["The Eiffel Tower is in Paris."],
        "labels": ["true"],
        "justifications": ["The Eiffel Tower is located in Paris, France."],
        "final_label": None,
        "final_justification": None
    }

    def verdict_agent_run():
        return verdict_agent.invoke(initial_state)

    result = benchmark(verdict_agent_run)
    assert result is not None, "Verdict agent returned no result"
