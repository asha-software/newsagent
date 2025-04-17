from types import ModuleType
from typing import Any, List, Mapping
from unittest.mock import patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama


def claim_decomposer_uut(monkeypatch) -> ModuleType:
    monkeypatch.setenv("CLAIM_DECOMPOSER_MODEL", "mistral:7b")
    import core.agents.claim_decomposer as claim_decomposer

    return claim_decomposer


def test_preprocessing_adds_expected_messages(monkeypatch):
    claim_decomposer = claim_decomposer_uut(monkeypatch)

    state_in: Mapping[str, Any] = {"text": "Birds sing at dawn."}
    state_out = claim_decomposer.preprocessing(dict(state_in))
    msgs: List[Any] = state_out["messages"]
    assert len(msgs) == 2
    assert isinstance(msgs[0], SystemMessage)
    assert msgs[0] is claim_decomposer.system_message
    assert isinstance(msgs[1], HumanMessage)
    assert msgs[1].content == state_in["text"]


def test_assistant_invokes_llm_and_returns_ai_message(monkeypatch):
    claim_decomposer = claim_decomposer_uut(monkeypatch)

    with patch.object(
        ChatOllama, "invoke", return_value=AIMessage(content='["fact"]')
    ) as mock_invoke:
        dummy_state = {"messages": ["any"]}
        ret = claim_decomposer.assistant(dummy_state)
        assert dummy_state["messages"] is mock_invoke.call_args_list[0].args[0]
        print(ret)
        assert isinstance(ret["messages"], AIMessage)
        assert ret["messages"].content == '["fact"]'


def test_postprocessing_happy_path(monkeypatch):
    claim_decomposer = claim_decomposer_uut(monkeypatch)
    ai_msg = AIMessage(content='["claim‑A", "claim‑B"]')
    result = claim_decomposer.postprocessing({"messages": [ai_msg]})
    assert result == {"claims": ["claim‑A", "claim‑B"]}


def test_postprocessing_raises_on_bad_json(monkeypatch):
    """
    Check if we receive an UnboundLocalError when JSON decoding fails
    """
    claim_decomposer = claim_decomposer_uut(monkeypatch)
    ai_msg = AIMessage(content="NOT‑JSON")
    with pytest.raises(UnboundLocalError):
        claim_decomposer.postprocessing({"messages": [ai_msg]})


def test_stategraph_end_to_end(monkeypatch):
    """
    Drive the full LangGraph pipeline
    """
    claim_decomposer = claim_decomposer_uut(monkeypatch)
    with patch.object(
        ChatOllama,
        "invoke",
        return_value=[AIMessage(content='["sky is blue", "grass is green"]')],
    ) as mock_invoke:
        result = claim_decomposer.claim_decomposer.invoke(
            {"text": "The sky is blue and the grass is green."}
        )
        assert result["claims"] == ["sky is blue", "grass is green"]
        # Ensure the LLM was actually consulted once
        assert mock_invoke.call_count == 1
