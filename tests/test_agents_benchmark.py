import pytest
import time
from core.agents.claim_decomposer import claim_decomposer
from core.agents.research_agent import create_agent
from core.agents.reasoning_agent import reasoning_agent
from core.agents.verdict_agent import verdict_agent

@pytest.mark.benchmark
def test_claim_decomposer_benchmark():
    """Benchmark the claim decomposer agent."""
    initial_state = {"text": "The sky is blue and the grass is green."}

    start_time = time.time()
    result = claim_decomposer.invoke(initial_state)
    end_time = time.time()

    elapsed_time = end_time - start_time
    print(f"Elapsed time for claim decomposer: {elapsed_time:.2f} seconds")
    print(f"Decomposed claims: {result['claims']}")

    assert result is not None, "Claim decomposer returned no result"
    assert elapsed_time < 100, "Claim decomposer took too long"

@pytest.mark.benchmark
def test_research_agent_benchmark():
    """Benchmark the research agent."""
    builtin_tools_wanted = ['wikipedia', 'web_search']
    research_agent = create_agent(model='mistral-nemo', builtin_tools=builtin_tools_wanted)

    initial_state = {"claim": "Python was created by Guido van Rossum"}

    start_time = time.time()
    result = research_agent.invoke(initial_state)
    end_time = time.time()

    elapsed_time = end_time - start_time
    print(f"Elapsed time for research agent: {elapsed_time:.2f} seconds")
    print(f"Evidence: {result['evidence']}")

    assert result is not None, "Research agent returned no result"
    assert elapsed_time < 500, "Research agent took too long"

@pytest.mark.benchmark
def test_reasoning_agent_benchmark():
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

    start_time = time.time()
    result = reasoning_agent.invoke(initial_state)
    end_time = time.time()

    elapsed_time = end_time - start_time
    print(f"Elapsed time for reasoning agent: {elapsed_time:.2f} seconds")
    print(f"Label: {result['label']}, Justification: {result['justification']}")

    assert result is not None, "Reasoning agent returned no result"
    assert elapsed_time < 500, "Reasoning agent took too long"

@pytest.mark.benchmark
def test_verdict_agent_benchmark():
    """Benchmark the verdict agent."""
    initial_state = {
        "messages": [],
        "claims": ["The Eiffel Tower is in Paris."],
        "labels": ["true"],
        "justifications": ["The Eiffel Tower is located in Paris, France."],
        "final_label": None,
        "final_justification": None
    }

    start_time = time.time()
    result = verdict_agent.invoke(initial_state)
    end_time = time.time()

    elapsed_time = end_time - start_time
    print(f"Elapsed time for verdict agent: {elapsed_time:.2f} seconds")
    print(f"Final Label: {result['final_label']}, Final Justification: {result['final_justification']}")

    assert result is not None, "Verdict agent returned no result"
    assert elapsed_time < 100, "Verdict agent took too long"
