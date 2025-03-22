import pytest
import sys
import os
from unittest.mock import patch, MagicMock
from pathlib import Path

# Add project root to Python path if not already added
project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.agents.research_agent_simplified import agent, State
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage


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
    assert "used_tools" in final_state, "Final state should contain used_tools"


def test_tool_usage():
    """Test that tools are properly called and results are captured"""
    claim = "Python is a programming language"
    result = agent.invoke({"claim": claim})

    assert len(result["evidence"]
               ) > 0, "Evidence list should contain tool results"
    
    assert len(result["used_tools"]) > 0, "At least one tool should be used"
    
    for evidence in result["evidence"]:
        tool_name = evidence["name"]
        assert tool_name in result["used_tools"], f"Tool {tool_name} should be in used tools"


def test_empty_claim():
    """Test behavior with empty claim"""
    result = agent.invoke({"claim": ""})
    assert "messages" in result, "Result should handle empty claims gracefully"
    assert "used_tools" in result, "Result should contain used tools even for empty claims"


def test_calculator_tool_usage():
    """Test that calculator tools are used for mathematical claims"""
    claim = "12 multiplied by 10 equals 120"
    result = agent.invoke({"claim": claim})

    calculator_used = any(
        tool_name in result["used_tools"]
        for tool_name in ["multiply", "add", "divide"]
    )
    assert calculator_used, "At least one calculator tool should be used for mathematical claims"


def test_wikipedia_tool_usage():
    """Test that Wikipedia tool is used for factual claims"""
    claim = "Albert Einstein developed the theory of relativity"
    result = agent.invoke({"claim": claim})

    assert "query" in result["used_tools"], "Wikipedia query tool should be used for factual claims"


def test_mixed_claim():
    """Test behavior with a claim that might need multiple tools"""
    claim = "If you multiply the distance from Earth to the Sun (93 million miles) by 2, you get 186 million miles"
    result = agent.invoke({"claim": claim})

    assert len(result["used_tools"]) > 0, "At least one tool should be used for mixed claims"
    
    assert len(result["evidence"]) > 0, "Should gather evidence for mixed claims"
