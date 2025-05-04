# tests/test_research_agent_calculator.py
"""
Combined *integration* + *plumbing* tests for the Research Agent’s
interaction with the builtin **calculator** tool.


Almost identical to your original file.  We monkey-patch both
`import_builtin("calculator")` and `get_chat_model` so the whole thing
runs instantly and deterministically, exercising many claims.
"""
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage, ToolMessage

# ------------------------------------------------------------------
# Common helper: build a Research-Agent on demand
# ------------------------------------------------------------------
import core.agents.research_agent as ra

# ==================================================================
# PART II –  Plumbing (stub / fast)            ─────────────────────
# ==================================================================


# ---------- Dummy calculator tool ---------------------------------
def dummy_calculator():
    """
    Lightweight replacement for the real calculator: evaluates a plain
    Python arithmetic expression and returns the result as *string*.
    """

    def tool_function(expression: str) -> str:  # noqa: D401
        """Compute `expression` and return the result as a string."""
        try:
            return str(eval(expression, {}, {}))
        except Exception:
            return "error"

    tool_function.__doc__ += "\nStub used in unit tests."
    return tool_function


# ---------- Helpers -----------------------------------------------
def make_ai_and_tool_msgs(expr: str, result: str):
    tool_call_id = "calc-1"
    ai = AIMessage(
        content="Let me calculate that.",
        tool_calls=[
            {"id": tool_call_id, "name": "calculator", "args": {"expression": expr}}
        ],
    )
    tool_msg = ToolMessage(content=result, tool_call_id=tool_call_id)
    return [ai, tool_msg]


STUB_MATRIX = [
    # should_use , claim text                                , expression , expected
    (True, "The sum of 13 and 29 equals 42.", "13+29", "42"),
    (True, "4.5 times 8.2 is 36.9.", "4.5*8.2", "36.9"),
    (True, "There are 365 days in a non-leap year.", "360+5", "365"),
    (True, "Fifty minus seventeen is thirty-three.", "50-17", "33"),
    (True, "9 squared equals 81.", "9**2", "81"),
    (False, "Paris is the capital of France.", "", ""),
    (False, "Lionel Messi is an Argentine footballer.", "", ""),
    (False, "The Pacific Ocean is the largest ocean.", "", ""),
    (False, "Photosynthesis converts CO₂ into glucose.", "", ""),
    (False, "The Eiffel Tower is in Paris.", "", ""),
]


@pytest.mark.parametrize(("should_use", "claim", "expr", "expected"), STUB_MATRIX)
def test_research_agent_stub(monkeypatch, should_use, claim, expr, expected):
    """
    Fast unit-test layer.

    We monkey-patch:
      • `import_builtin("calculator")` to return `dummy_calculator`;
      • `get_chat_model` so the “LLM” produces a canned Tool-call or not.

    Then we assert on the evidence list.
    """
    # Patch 1 – stub calculator
    monkeypatch.setattr(
        ra,
        "import_builtin",
        lambda name: dummy_calculator() if name == "calculator" else None,
        raising=True,
    )

    # Patch 2 – deterministic fake LLM
    fake_llm = SimpleNamespace()
    fake_llm.bind_tools = lambda tools: fake_llm
    if should_use:
        msgs = make_ai_and_tool_msgs(expr, expected)
    else:
        msgs = [AIMessage(content="No calculation needed.", tool_calls=[])]
    fake_llm.invoke = lambda *_: msgs
    monkeypatch.setattr(ra, "get_chat_model", lambda *_, **__: fake_llm, raising=True)

    # Build agent
    agent = ra.create_agent(model="dummy", builtin_tools=["calculator"])

    state = agent.invoke({"claim": claim})
    evidence = state["evidence"]

    if should_use:
        assert len(evidence) == 1
        ev = evidence[0]
        assert ev["name"] == "calculator"
        assert ev["args"]["expression"] == expr
        assert ev["result"] == expected
    else:
        assert evidence == []
