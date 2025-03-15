import pytest
from unittest.mock import patch, MagicMock
from langsmith import testing as t
from pathlib import Path
# Project root added to pythonpath in pyproject.toml, allowing these imports:
from core.agents.research_agent import agent, State
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage


# @pytest.fixture
# def mock_llm_response():
#     """Fixture to mock LLM responses with tool calls"""
#     with patch("core.agents.research_agent.llm") as mock_llm:        # Create a mock AIMessage with tool calls for testing        tool_call = {            "name": "query",            "args": {"query": "Python programming language"},            "id": "call_123"        }        mock_response = AIMessage(            content="I'll search for information about Python.",            tool_calls=[tool_call]        )        mock_llm.invoke.return_value = mock_response        yield mock_llm@pytest.fixturedef mock_tool_execution():
#         """Fixture to mock tool execution"""
#         with patch("langgraph.prebuilt.ToolNode") as mock_tool_node:
#             # Configure the mock to add a tool message to the state
#             def side_effect(state):
#                 messages = state.get("messages", [])
#                 tool_message = ToolMessage(
#                     content="Python is a programming language.",
#                     tool_call_id="call_123"
#                 )
#                 return {"messages": messages + [tool_message]}

#             mock_instance = MagicMock()
#             mock_instance.side_effect = side_effect
#             mock_tool_node.return_value = mock_instance
#             yield mock_tool_node


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


def test_tool_usage():
    """Test that tools are properly called and results are captured"""
    claim = "Python is a programming language"
    result = agent.invoke({"claim": claim})

    assert len(result["evidence"]
               ) > 0, "Evidence list should contain tool results"
    assert result["evidence"][0]["name"] == "query", "Tool name should be recorded"
    assert "Python" in result["evidence"][0]["result"], "Tool result should be recorded"


def test_empty_claim():
    """Test behavior with empty claim"""
    result = agent.invoke({"claim": "", "messages": [], "evidence": []})
    assert "messages" in result, "Result should handle empty claims gracefully"


def test_calculator_tool():
    """Integration test for calculator tool usage"""
    claim = "12 multiplied by 10 equals 120"
    result = agent.invoke({"claim": claim, "messages": [], "evidence": []})

    # Check if any calculator tool was used in evidence
    calculator_used = any(
        evidence["name"] in ["multiply", "add", "divide"]
        for evidence in result["evidence"]
    )
    assert calculator_used, "Calculator tool should be used for mathematical claims"


def test_wikipedia_tool():
    """Integration test for Wikipedia tool usage"""
    claim = "Albert Einstein developed the theory of relativity"
    result = agent.invoke({"claim": claim, "messages": [], "evidence": []})

    # Check if Wikipedia query tool was used in evidence
    wikipedia_used = any(
        evidence["name"] == "query" for evidence in result["evidence"]
    )
    assert wikipedia_used, "Wikipedia tool should be used for historical claims"
