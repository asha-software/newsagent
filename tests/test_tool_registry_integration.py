import unittest.mock
import ast
import pytest
from langchain_core.messages import AIMessage
from core.agents.research_agent import create_agent


#############################
# Helper / Mock definitions #
#############################

class _MockHTTPResponse:
    """Very small stub that mimics the part of the *requests* response we need."""

    def __init__(self, payload):
        self._payload = payload

    def json(self):  # noqa: D401 – short & sweet
        return self._payload

    # Fallback so that ``str(response)`` is still readable when LangGraph casts
    def __str__(self):  # pragma: no cover – representation only
        return str(self._payload)


########################
# Pytest‑level fixtures #
########################

@pytest.fixture()
def dummy_tool_kwargs():
    """Return *kwargs used to create a very small service tool.

    The tool will hit ``https://dummy.api/item`` but we monkey‑patch
    ``requests.request`` in the tests so no outbound traffic is ever made.
    """

    return {
        "name": "dummy_service",
        "method": "GET",
        "url_template": "https://dummy.api/item",
        "docstring": "Fetches a dummy field from a mock API and returns it as a list.",
        # Pull out the single scalar so the return type is JSON‑serialisable / str‑able.
        "target_fields": [["field"]],
        "param_mapping": {},  # ← no runtime parameters required for this very simple case
    }


@pytest.fixture()
def patched_requests(monkeypatch):
    """Monkey‑patch *requests.request* so no real HTTP occurs."""

    def _fake_request(*_args, **_kwargs):  # noqa: D401 – tiny helper
        return _MockHTTPResponse({"field": "dummy_value"})

    monkeypatch.setattr("requests.request", _fake_request, raising=False)
    # The test body can now run without touching the network.


#####################
# Integration tests #

###############################
# Extra coverage for api_caller
###############################

def test_agent_mixed_param_locations(monkeypatch):
    """Full agent run exercising header/param/data/json mapping"""

    captured_call = {}

    def _fake_request(method, url, headers=None, params=None, data=None, json=None):
        captured_call.update({
            "method": method,
            "url": url,
            "headers": headers,
            "params": params,
            "data": data,
            "json": json,
        })
        return _MockHTTPResponse({"ok": True})

    monkeypatch.setattr("requests.request", _fake_request)

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

    # --------------------
    # Mock assistant steps
    # --------------------
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

    mocked_llm = unittest.mock.MagicMock()
    mocked_llm.bind_tools.return_value = mocked_llm
    mocked_llm.invoke.side_effect = [[first_turn], [second_turn]]

    with unittest.mock.patch(
            "core.agents.research_agent.get_chat_model", return_value=mocked_llm
    ):
        agent = create_agent(
            model="whatever",
            builtin_tools=[],
            user_tool_kwargs=[tool_def],
        )

    # Run the graph – should execute into ToolNode and make HTTP request
    agent.invoke({"claim": "irrelevant"})

    # Validate HTTP mapping
    assert captured_call["method"] == "POST"
    assert captured_call["url"] == "https://api.example.com/users/alice"
    assert captured_call["headers"]["Accept"] == "application/json"
    assert captured_call["headers"]["token"] == "secrettoken"
    assert captured_call["params"] == {"verbose": True}
    assert captured_call["json"] == {"bio": "Hello!"}
    assert captured_call["data"] == {"note": "something"}



def _deserialize_tool_result(result_str: str):
    """Tool messages arrive as *strings*. Convert to Python safely if possible."""
    try:
        return ast.literal_eval(result_str)
    except (SyntaxError, ValueError):
        return result_str



def test_multiple_user_tools_register_and_execute_sequentially(
        dummy_tool_kwargs, patched_requests
):
    """create_agent with two tools -> both results captured."""

    tool_kwargs_one = dummy_tool_kwargs.copy()
    tool_kwargs_two = dummy_tool_kwargs.copy()
    tool_kwargs_one["name"] = "service_one"
    tool_kwargs_one["target_fields"] = [["field1"]]
    tool_kwargs_two["name"] = "service_two"
    tool_kwargs_two["target_fields"] = [["field2"]]

    def _fake_request(*_args, **_kwargs):
        return _MockHTTPResponse({"field1": "value‑one", "field2": "value‑two"})

    with unittest.mock.patch("requests.request", _fake_request):
        first_turn = AIMessage(
            content="Need both pieces of information…",
            tool_calls=[
                {"id": "c1", "name": "service_one", "args": {}},
                {"id": "c2", "name": "service_two", "args": {}},
            ],
        )
        second_turn = AIMessage(content="done", tool_calls=[])

        mocked_llm = unittest.mock.MagicMock()
        mocked_llm.bind_tools.return_value = mocked_llm
        mocked_llm.invoke.side_effect = [[first_turn], [second_turn]]

        with unittest.mock.patch(
                "core.agents.research_agent.get_chat_model", return_value=mocked_llm
        ):
            agent = create_agent(
                model="any‑model",
                builtin_tools=[],
                user_tool_kwargs=[tool_kwargs_one, tool_kwargs_two],
            )

        state = agent.invoke({"claim": "collect info"})
        ev_list = state["evidence"]
        assert {e["name"] for e in ev_list} == {"service_one", "service_two"}

        # Safely parse the list‑string coming from the ToolMessage.
        parsed_results = {
            e["name"]: _deserialize_tool_result(e["result"])
            for e in ev_list
        }
        assert parsed_results["service_one"][0] == "value‑one"
        assert parsed_results["service_two"][0] == "value‑two"

import unittest.mock
import pytest

from langchain_core.messages import AIMessage

from core.agents.research_agent import create_agent

###############################################################################
# Tiny helper: fake *requests* response object                                #
###############################################################################

class _MockResponse:
    """Mimic the minimal surface of *requests.Response* used by api_caller."""

    def __init__(self, payload):
        self._payload = payload

    def json(self):  # noqa: D401 – concise helper
        return self._payload

    def __str__(self):  # pragma: no cover – representational only
        return str(self._payload)

###############################################################################
# Utility to run an agent once and capture its evidence                        #
###############################################################################

def _run_agent_once(agent):
    """Run *agent.invoke* exactly once for a dummy claim and return evidence list."""
    state = agent.invoke({"claim": "integration"})
    return state["evidence"]

###############################################################################
# 1. INT‑INDEX path of *extract_fields* (line ~27) via agent                   #
###############################################################################

def test_agent_list_index_extract_fields(monkeypatch):
    """Full graph run hitting the *int index* branch inside *extract_fields*."""

    # ------------------------------------------------------------------
    # Patch *requests.request* so the tool receives a JSON list payload
    # ------------------------------------------------------------------
    def _fake_request(*_args, **_kwargs):
        return _MockResponse([
            {"value": "alpha"},
            {"value": "bravo"},
        ])

    monkeypatch.setattr("requests.request", _fake_request)

    # -------------------------------
    # Define the user tool for agent
    # -------------------------------
    tool_def = {
        "name": "list_tool",
        "method": "GET",
        "url_template": "https://example.com/items",
        "target_fields": [[0, "value"]],  # ← starts with *int* so branch executes
        "param_mapping": {},
    }

    # ---------------------------------------------
    # Mock the LLM so it immediately calls list_tool
    # ---------------------------------------------
    first_turn = AIMessage(
        content="call list_tool",
        tool_calls=[{
            "id": "call‑1",
            "name": "list_tool",
            "args": {},
        }],
    )
    second_turn = AIMessage(content="done", tool_calls=[])

    mocked_llm = unittest.mock.MagicMock()
    mocked_llm.bind_tools.return_value = mocked_llm
    mocked_llm.invoke.side_effect = [[first_turn], [second_turn]]

    with unittest.mock.patch("core.agents.research_agent.get_chat_model", return_value=mocked_llm):
        agent = create_agent(model="irrelevant", builtin_tools=[], user_tool_kwargs=[tool_def])

    evidence = _run_agent_once(agent)

    import ast
    parsed = ast.literal_eval(evidence[0]["result"]) if isinstance(evidence[0]["result"], str) else evidence[0]["result"]
    assert parsed == ["alpha"]

###############################################################################
# 2. hasattr / object attribute branch (line ~31) via agent                    #
###############################################################################

def test_agent_object_attribute_extract_fields(monkeypatch):
    """Full graph run hitting *hasattr* → *getattr* path in *extract_fields*."""

    class _Obj:
        def __init__(self):
            self.answer = 42

    def _fake_request(*_args, **_kwargs):
        return _MockResponse(_Obj())

    monkeypatch.setattr("requests.request", _fake_request)

    tool_def = {
        "name": "attr_tool",
        "method": "GET",
        "url_template": "https://example.com/answer",
        "target_fields": [["answer"]],  # triggers hasattr branch
        "param_mapping": {},
    }

    first_turn = AIMessage(
        content="call attr_tool",
        tool_calls=[{"id": "c1", "name": "attr_tool", "args": {}}],
    )
    second_turn = AIMessage(content="done", tool_calls=[])

    mocked_llm = unittest.mock.MagicMock()
    mocked_llm.bind_tools.return_value = mocked_llm
    mocked_llm.invoke.side_effect = [[first_turn], [second_turn]]

    with unittest.mock.patch("core.agents.research_agent.get_chat_model", return_value=mocked_llm):
        agent = create_agent(model="x", builtin_tools=[], user_tool_kwargs=[tool_def])

    evidence = _run_agent_once(agent)
    import ast
    parsed = ast.literal_eval(evidence[0]["result"]) if isinstance(evidence[0]["result"], str) else evidence[0]["result"]
    assert parsed == [42]

###############################################################################
# 3. param_mapping into *json* body branch (line ~104) via agent               #
###############################################################################

def test_agent_json_param_mapping(monkeypatch):
    """Ensure param routed to JSON payload when *param_mapping for == 'json'*."""

    captured = {}

    def _fake_request(method, url, json=None, **_kwargs):
        captured.update({"method": method, "url": url, "json": json})
        return _MockResponse({"ok": True})

    monkeypatch.setattr("requests.request", _fake_request)

    tool_def = {
        "name": "json_tool",
        "method": "POST",
        "url_template": "https://example.com/post",
        "param_mapping": {
            "foo": {"type": "str", "for": "json"},
        },
    }

    first_turn = AIMessage(
        content="post with foo",
        tool_calls=[{"id": "call‑json", "name": "json_tool", "args": {"foo": "bar"}}],
    )
    second_turn = AIMessage(content="done", tool_calls=[])

    mocked_llm = unittest.mock.MagicMock()
    mocked_llm.bind_tools.return_value = mocked_llm
    mocked_llm.invoke.side_effect = [[first_turn], [second_turn]]

    with unittest.mock.patch("core.agents.research_agent.get_chat_model", return_value=mocked_llm):
        agent = create_agent(model="m", builtin_tools=[], user_tool_kwargs=[tool_def])

    evidence = _run_agent_once(agent)

    # Basic correctness check
    import ast
    parsed_result = ast.literal_eval(evidence[0]["result"]) if isinstance(evidence[0]["result"], str) else evidence[0]["result"].json()
    assert parsed_result["ok"] is True
    assert captured["json"] == {"foo": "bar"}  # mapping landed in payload
