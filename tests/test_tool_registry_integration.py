import ast
import unittest.mock as mock
from typing import Any, Dict

import pytest
from langchain_core.messages import AIMessage

from core.agents.research_agent import create_agent

###############################################################################
# Helpers / fixtures
###############################################################################


class _MockHTTPResponse:
    """Very small stub that mimics the part of the *requests* response we need."""

    def __init__(self, payload: Any):
        self._payload = payload

    def json(self) -> Any:  # noqa: D401 – short & sweet
        return self._payload

    def __str__(self) -> str:  # pragma: no cover – representation only
        return str(self._payload)


def _deserialize_tool_result(result_str: str | Any) -> Any:
    """Convert *ToolMessage* string‑payloads back to Python if possible."""
    if not isinstance(result_str, str):
        return result_str
    try:
        return ast.literal_eval(result_str)
    except (SyntaxError, ValueError):
        return result_str


@pytest.fixture()
def capture_requests(monkeypatch):  # noqa: D401 – pytest fixture
    """Capture arguments to *requests.request* and allow the test body to inspect them."""

    captured: Dict[str, Any] = {}

    def _fake_request(method: str, url: str, **kwargs: Any):  # noqa: D401 – helper
        captured.update({"method": method, "url": url, **kwargs})
        # Echo the JSON payload back so the test can assert on it if required.
        return _MockHTTPResponse(kwargs.get("json", {"ok": True}))

    monkeypatch.setattr("requests.request", _fake_request)
    return captured


###############################################################################
# Tiny helper to exercise the agent exactly once
###############################################################################


def _run_agent_once(agent):
    return agent.invoke({"claim": "integration"})["evidence"]


###############################################################################
# Tests
###############################################################################


def test_agent_mixed_param_locations(capture_requests):
    """A header/param/data/json/url‑param mapping smoke‑test."""

    tool_def = {
        "name": "mixed_tool",
        "method": "POST",
        "url_template": "https://api.example.com/users/{username}",
        "headers": {"Accept": "application/json"},
        "param_mapping": {
            "username": {"type": "str", "for": "url_params"},
            "token": {"type": "str", "for": "headers"},
            "verbose": {"type": "bool", "for": "params"},
            "bio": {"type": "str", "for": "json"},
            "note": {"type": "str", "for": "data"},
        },
    }

    first_turn = AIMessage(
        content="Trigger mixed_tool",
        tool_calls=[
            {
                "id": "call‑mixed",
                "name": "mixed_tool",
                "args": {
                    "username": "alice",
                    "token": "secrettoken",
                    "verbose": True,
                    "bio": "Hello!",
                    "note": "something",
                },
            }
        ],
    )

    second_turn = AIMessage(content="done", tool_calls=[])

    mocked_llm = mock.MagicMock()
    mocked_llm.bind_tools.return_value = mocked_llm
    mocked_llm.invoke.side_effect = [[first_turn], [second_turn]]

    with mock.patch(
        "core.agents.research_agent.get_chat_model", return_value=mocked_llm
    ):
        agent = create_agent(
            "irrelevant", builtin_tools=[], user_tool_kwargs=[tool_def]
        )

    _run_agent_once(agent)
    captured = capture_requests

    assert captured["method"] == "POST"
    assert captured["url"] == "https://api.example.com/users/alice"
    assert captured["headers"]["Accept"] == "application/json"
    assert captured["headers"]["token"] == "secrettoken"
    assert captured["params"] == {"verbose": True}
    assert captured["json"] == {"bio": "Hello!"}
    assert captured["data"] == {"note": "something"}


def test_multiple_user_tools_register_and_execute_sequentially(monkeypatch):
    """Two user‑defined tools register and their results are captured independently."""

    def _fake_request(*_args, **_kwargs):
        return _MockHTTPResponse({"field1": "value‑one", "field2": "value‑two"})

    monkeypatch.setattr("requests.request", _fake_request)

    def _tool(name: str, field: str):
        kw = {
            "name": name,
            "method": "GET",
            "url_template": "https://dummy.api/item",
            "docstring": "dummy",
            "target_fields": [[field]],
            "param_mapping": {},
        }
        return kw

    tool_kwargs = [_tool("service_one", "field1"), _tool("service_two", "field2")]

    first_turn = AIMessage(
        content="Need both pieces …",
        tool_calls=[
            {"id": "c1", "name": "service_one", "args": {}},
            {"id": "c2", "name": "service_two", "args": {}},
        ],
    )
    second_turn = AIMessage(content="done", tool_calls=[])

    mocked_llm = mock.MagicMock()
    mocked_llm.bind_tools.return_value = mocked_llm
    mocked_llm.invoke.side_effect = [[first_turn], [second_turn]]

    with mock.patch(
        "core.agents.research_agent.get_chat_model", return_value=mocked_llm
    ):
        agent = create_agent("model‑x", builtin_tools=[], user_tool_kwargs=tool_kwargs)

    evidence = _run_agent_once(agent)
    parsed = {e["name"]: _deserialize_tool_result(e["result"])[0] for e in evidence}

    assert parsed == {"service_one": "value‑one", "service_two": "value‑two"}


def test_agent_list_index_extract_fields(monkeypatch):
    """Extraction from a list‑payload via positional index and key."""

    def _fake_request(*_args, **_kwargs):
        return _MockHTTPResponse([{"value": "alpha"}, {"value": "bravo"}])

    monkeypatch.setattr("requests.request", _fake_request)

    tool_def = {
        "name": "list_tool",
        "method": "GET",
        "url_template": "https://example.com/items",
        "target_fields": [[0, "value"]],
        "param_mapping": {},
    }

    first_turn = AIMessage(
        content="call list_tool",
        tool_calls=[{"id": "call‑1", "name": "list_tool", "args": {}}],
    )
    second_turn = AIMessage(content="done", tool_calls=[])

    mocked_llm = mock.MagicMock()
    mocked_llm.bind_tools.return_value = mocked_llm
    mocked_llm.invoke.side_effect = [[first_turn], [second_turn]]

    with mock.patch(
        "core.agents.research_agent.get_chat_model", return_value=mocked_llm
    ):
        agent = create_agent(
            "irrelevant", builtin_tools=[], user_tool_kwargs=[tool_def]
        )

    evidence = _run_agent_once(agent)
    assert _deserialize_tool_result(evidence[0]["result"]) == ["alpha"]


def test_agent_object_attribute_extract_fields(monkeypatch):
    """Extraction from an object attribute (uses *hasattr* path)."""

    class _Obj:
        def __init__(self) -> None:
            self.answer = 42

    monkeypatch.setattr(
        "requests.request", lambda *_a, **_kw: _MockHTTPResponse(_Obj())
    )

    tool_def = {
        "name": "attr_tool",
        "method": "GET",
        "url_template": "https://example.com/answer",
        "target_fields": [["answer"]],
        "param_mapping": {},
    }

    first_turn = AIMessage(
        content="call", tool_calls=[{"id": "c1", "name": "attr_tool", "args": {}}]
    )
    second_turn = AIMessage(content="done", tool_calls=[])

    mocked_llm = mock.MagicMock()
    mocked_llm.bind_tools.return_value = mocked_llm
    mocked_llm.invoke.side_effect = [[first_turn], [second_turn]]

    with mock.patch(
        "core.agents.research_agent.get_chat_model", return_value=mocked_llm
    ):
        agent = create_agent("x", builtin_tools=[], user_tool_kwargs=[tool_def])

    evidence = _run_agent_once(agent)
    assert _deserialize_tool_result(evidence[0]["result"]) == [42]


def test_agent_json_param_mapping(capture_requests):
    """Parameters flagged for *json* location land in the request body."""

    tool_def = {
        "name": "json_tool",
        "method": "POST",
        "url_template": "https://example.com/post",
        "param_mapping": {"foo": {"type": "str", "for": "json"}},
    }

    first_turn = AIMessage(
        content="post with foo",
        tool_calls=[{"id": "call", "name": "json_tool", "args": {"foo": "bar"}}],
    )
    second_turn = AIMessage(content="done", tool_calls=[])

    mocked_llm = mock.MagicMock()
    mocked_llm.bind_tools.return_value = mocked_llm
    mocked_llm.invoke.side_effect = [[first_turn], [second_turn]]

    with mock.patch(
        "core.agents.research_agent.get_chat_model", return_value=mocked_llm
    ):
        agent = create_agent("x", builtin_tools=[], user_tool_kwargs=[tool_def])

    evidence = _run_agent_once(agent)

    # The fake request echoes JSON back so the agent result contains it directly.
    assert _deserialize_tool_result(evidence[0]["result"])["foo"] == "bar"
    assert capture_requests["json"] == {"foo": "bar"}
