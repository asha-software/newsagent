"""
Unit–tests for the Research-Agent’s interaction with the builtin **calculator** tool.

The tests monkey-patch `core.agents.research_agent.import_builtin("calculator")`
with a lightweight stub that:

1. evaluates a plain Python arithmetic expression;
2. returns the result as a string, exactly the way the real calculator tool does.

We then verify that the Research Agent calls (or does **not** call) the
calculator in the appropriate situations and that the `ToolMessage` produced
contains the expected value.
"""

from types import SimpleNamespace
import pytest
from langchain_core.messages import AIMessage, ToolMessage

# Dummy calculator tool
def dummy_calculator():
    """
    Factory that returns a calculator tool.
    """
    def tool_function(expression: str) -> str:
        """Calculator tool: evaluate arithmetic expression and return the result as a string."""
        try:
            return str(eval(expression, {}, {}))
        except Exception:
            return "error"

    return tool_function


# Helpers used in the parametrised test
def make_ai_and_tool_msgs(expr: str, result: str) -> list:
    """Return the pair `[AIMessage(tool_call), ToolMessage(result)]`."""
    tool_call_id = "calc-1"
    ai = AIMessage(
        content="Let me calculate that.",
        tool_calls=[{"id": tool_call_id, "name": "calculator", "args": {"expression": expr}}],
    )
    tool_msg = ToolMessage(content=result, tool_call_id=tool_call_id)
    return [ai, tool_msg]


TEST_MATRIX = [
    # should_use , claim text                                 , expression , expected
    (True,  "The sum of 13 and 29 equals 42."                , "13+29" , "42"),
    (True,  "4.5 times 8.2 is 36.9."                         , "4.5*8.2", "36.9"),
    (True,  "There are 365 days in a non-leap year."         , "360+5" , "365"),
    (True,  "Fifty minus seventeen is thirty-three."         , "50-17" , "33"),
    (True,  "9 squared equals 81."                           , "9**2"  , "81"),
    (False, "Paris is the capital of France."                , "",      ""),
    (False, "Lionel Messi is an Argentine footballer."       , "",      ""),
    (False, "The Pacific Ocean is the largest ocean."        , "",      ""),
    (False, "Photosynthesis converts CO₂ into glucose."      , "",      ""),
    (False, "The Eiffel Tower is in Paris."                  , "",      ""),
]


# The single parametrised test
@pytest.mark.parametrize("should_use,claim,expr,expected", TEST_MATRIX)
def test_calculator_use_cases(monkeypatch, should_use, claim, expr, expected):
    """
    If the claim requires calculation (`should_use==True`)
    the Research Agent must:

      • emit an `AIMessage` containing a calculator tool-call with the *exact*
        `expression` we expect;
      • emit the corresponding `ToolMessage` whose content equals `expected`;
      • include that evidence in the final state.

    Otherwise (non-numeric claim) it must **not** call the calculator at all.
    """

    # Patch 1 – give the agent our stub calculator via import_builtin
    import core.agents.research_agent as ra

    monkeypatch.setattr(ra, "import_builtin", lambda name: dummy_calculator() if name == "calculator" else None)

    # Patch 2 – swap the LLM with a deterministic fake
    fake_llm = SimpleNamespace()
    fake_llm.bind_tools = lambda tools: fake_llm

    if should_use:
        msgs = make_ai_and_tool_msgs(expr, expected)
    else:
        msgs = [AIMessage(content="I can answer without tools.", tool_calls=[])]

    fake_llm.invoke = lambda messages: msgs
    monkeypatch.setattr(ra, "get_chat_model", lambda model_name: fake_llm)

    # Build agent (only calculator builtin is relevant here)
    agent = ra.create_agent(
        model="dummy-model",
        builtin_tools=["calculator"],
        user_tool_kwargs=[],
    )

    final_state = agent.invoke({"claim": claim})

    # Assertions
    if should_use:
        # one piece of evidence
        ev = final_state["evidence"]
        assert len(ev) == 1
        assert ev[0]["name"] == "calculator"
        assert ev[0]["args"]["expression"] == expr
        assert ev[0]["result"] == expected
    else:
        # no evidence means no tool call
        assert final_state["evidence"] == []
