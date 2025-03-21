import pytest
from unittest.mock import patch, MagicMock
from langsmith import testing as t
from pathlib import Path
# Project root added to pythonpath in pyproject.toml, allowing this import:
from core.agents.research_agent import agent, State
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from tests.test_data.research_agent_test_cases import TOOL_USAGE_TEST_CASES


def test_import():
    assert agent is not None, "Agent should be imported successfully"


def test_agent_processes_claim():
    """Test that the agent can process a simple claim"""
    claim = "Python was created by Guido van Rossum"
    final_state = agent.invoke({"claim": claim})

    print(f"Final evidence: {final_state['evidence']}")
    print()
    assert len(final_state["messages"]
               ) >= 3, "Final state should have at least 3 messages: System, Human (claim) and AI (research agent response to claim)"
    assert len(final_state["evidence"]
               ) > 0, "Final state should contain evidence"


@pytest.mark.parametrize("test_case", TOOL_USAGE_TEST_CASES)
def test_tool_use(test_case):
    """Parameterized test for tool usage with different claims"""
    claim = test_case["claim"]
    expected_tools = set(test_case["expected_tools"])
    description = test_case["description"]

    final_state = agent.invoke(
        {"claim": claim, "messages": [], "evidence": []})
    tools_used = {evidence["name"] for evidence in final_state["evidence"]}

    # Check if the expected tools were used in evidence
    formatted_description = description.format(
        expected_tools=expected_tools,
        tools_used=tools_used
    )
    assert expected_tools == tools_used, formatted_description
