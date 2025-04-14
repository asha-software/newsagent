import pytest
from unittest.mock import patch
import json

from langchain_core.messages import BaseMessage, AIMessage
from langchain_ollama import ChatOllama
from build.lib.core.agents.common_types import Evidence


@pytest.fixture()
def reasoning_agent_uut(monkeypatch):
    monkeypatch.setenv("REASONING_AGENT_MODEL", "mistral:7b")
    import core.agents.reasoning_agent as reasoning_agent
    return reasoning_agent

@pytest.fixture
def sample_state(reasoning_agent_uut):
    """
    Provides a minimal valid State fixture for testing.
    """
    return reasoning_agent_uut.State(messages=[], claim="The sky is blue", evidence=[
        Evidence(name="Factbook", result="Earth's atmosphere causes scattering of blue light.", args={})
    ], label=None, justification=None)


@pytest.fixture
def no_evidence_state():
    """
    State fixture with no evidence, to test edge cases.
    """
    return {
        "messages": [],
        "claim": "Claim with no evidence.",
        "evidence": [],
        "label": None,
        "justification": None,
    }


@pytest.mark.parametrize("evidence_count", [0, 1, 2])
def test_preprocessing(reasoning_agent_uut, sample_state, evidence_count):
    """
    Test preprocessing with 0, 1, and multiple pieces of evidence.
    Verifies that the system message is correctly formatted
    and the final returned state includes the system + human messages.
    """
    # Adjust the sample_state's evidence to have `evidence_count` items
    sample_state["evidence"] = [
        {"name": f"source{i}", "result": f"result{i}"}
        for i in range(evidence_count)
    ]

    new_state = reasoning_agent_uut.preprocessing(sample_state)

    # Check that we added exactly 2 messages to the state
    assert len(new_state["messages"]) == 2

    system_msg = new_state["messages"][0]
    human_msg = new_state["messages"][1]

    # The system message should contain a bullet list with the evidence results
    for i in range(evidence_count):
        assert f"* source{i}: result{i}" in system_msg.content

    # The human message should contain the claim
    assert "Claim:" in human_msg.content
    assert sample_state["claim"] in human_msg.content


def test_assistant(reasoning_agent_uut, sample_state):
    """
    Test the assistant function ensures llm.invoke is called
    and the returned dictionary has the 'messages' from the LLM.
    """
    with patch.object(ChatOllama, 'invoke', return_value=[{"content": "Fake response"}]) as mock_invoke:
        mock_invoke.return_value = [{"content": "Fake response"}]
        # We need the state from preprocessing, because assistant expects "messages" in the correct form
        preprocessed_state = reasoning_agent_uut.preprocessing(sample_state)
        response_state = reasoning_agent_uut.assistant(preprocessed_state)
        mock_invoke.assert_called_once_with(preprocessed_state["messages"])
        assert "messages" in response_state
        assert response_state["messages"] == [{"content": "Fake response"}]


def test_postprocessing(reasoning_agent_uut, sample_state):
    sample_state["messages"] = [AIMessage(content=json.dumps({"label": "label", "justification": "justification"}))]
    output = reasoning_agent_uut.postprocessing(sample_state)
    assert output["label"] == "label"
    assert output["justification"] == "justification"

