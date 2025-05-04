# tests/test_research_agent_calculator.py
"""
Combined *integration* + *plumbing* tests for the Research Agent’s
interaction with the builtin **calculator** tool.

--------------------------------------------------------------------
PART I  –  Integration tests (real LLM, real calculator)
--------------------------------------------------------------------
Goal: make sure that with an actual language-model in the loop the agent
  • recognises when a claim needs arithmetic,
  • generates a calculator tool-call with the proper expression,
  • wires the ToolMessage back into `state["evidence"]`.
"""
import math
import pytest

# ------------------------------------------------------------------
# Common helper: build a Research-Agent on demand
# ------------------------------------------------------------------
import core.agents.research_agent as ra


# ==================================================================
# PART I –  Integration (real LLM)            ───────────────────────
# ==================================================================


def make_agent_with_calc_llm(model_name: str = "mistral-nemo"):
    "Return a Research-Agent instance that knows only the calculator tool."
    return ra.create_agent(model=model_name, builtin_tools=["calculator"])


INTEGRATION_CASES = [
    # expect_calc , claim text                                , expression , numeric_result
    (True, "The product of 7 and 8 is 56.", "7*8", 56),
    (True, "If you square 15 you get 225.", "15**2", 225),
    (True, "Twelve divided by three equals four.", "12/3", 4),
    (
        False,
        "Marvel Studios will release 'Avengers: Secret Wars' as a two‑part film in 2026.",
        None,
        None,
    ),
    (
        False,
        "The EU’s planned 2035 ban on new internal‑combustion cars will be postponed.",
        None,
        None,
    ),
]


@pytest.mark.parametrize("expect_calc,claim,expr,result", INTEGRATION_CASES)
def test_research_agent_integration(expect_calc, claim, expr, result):
    """
    Hit the **real** LLM + real calculator.

    • When `expect_calc` is True, one piece of evidence **must** be present
      and must come from the calculator with the exact numeric result.

    • Otherwise `state["evidence"]` must be empty (no tool call at all).
    """
    agent = make_agent_with_calc_llm()

    state = agent.invoke({"claim": claim})
    evidence = state["evidence"]

    if expect_calc:
        assert len(evidence) == 1, "Calculator call expected"
        ev = evidence[0]
        assert ev["name"] == "calculator"
        # expression may be simplified by the LLM (e.g., '7 * 8') so
        # we compare numerically:
        calc_out = float(ev["result"])
        assert math.isclose(calc_out, float(result)), ev
    else:
        assert evidence == []
