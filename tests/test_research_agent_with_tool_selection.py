import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
# Project root added to pythonpath in pyproject.toml, allowing these imports:
from core.agents.research_agent_with_tool_selection import agent, State
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
    assert "tool_selections" in final_state, "Final state should contain tool selections"


def test_tool_selection():
    """Test that the tool selection phase works correctly"""
    claim = "Python is a programming language"
    result = agent.invoke({"claim": claim})

    assert "tool_selections" in result, "Result should contain tool selections"
    
    # Check that at least one tool was selected
    selected_tools = [
        tool_name for tool_name, selection in result["tool_selections"].items()
        if selection.get("selected", False)
    ]
    assert len(selected_tools) > 0, "At least one tool should be selected"
    
    # For this claim, wikipedia should be selected but math tools probably not
    assert "wikipedia" in result["tool_selections"], "Tool selections should include wikipedia"
    assert result["tool_selections"]["wikipedia"].get("selected", False), "Wikipedia tool should be selected for this claim"


def test_tool_usage():
    """Test that tools are properly called and results are captured"""
    claim = "Python is a programming language"
    result = agent.invoke({"claim": claim})

    assert len(result["evidence"]
               ) > 0, "Evidence list should contain tool results"
    
    # Check that only selected tools were used
    for evidence in result["evidence"]:
        tool_name = evidence["name"]
        assert tool_name in result["tool_selections"], f"Tool {tool_name} should be in tool selections"
        assert result["tool_selections"][tool_name].get("selected", False), f"Tool {tool_name} should be selected"


def test_empty_claim():
    """Test behavior with empty claim"""
    result = agent.invoke({"claim": ""})
    assert "messages" in result, "Result should handle empty claims gracefully"
    assert "tool_selections" in result, "Result should contain tool selections even for empty claims"


def test_calculator_tool_selection():
    """Test that calculator tools are selected for mathematical claims"""
    claim = "12 multiplied by 10 equals 120"
    result = agent.invoke({"claim": claim})

    # Check that at least one calculator tool was selected
    calculator_selected = any(
        result["tool_selections"].get(tool_name, {}).get("selected", False)
        for tool_name in ["multiply", "add", "divide"]
    )
    assert calculator_selected, "At least one calculator tool should be selected for mathematical claims"


def test_wikipedia_tool_selection():
    """Test that Wikipedia tool is selected for factual claims"""
    claim = "Albert Einstein developed the theory of relativity"
    result = agent.invoke({"claim": claim})

    # Check that the Wikipedia tool was selected
    assert "wikipedia" in result["tool_selections"], "Tool selections should include wikipedia"
    assert result["tool_selections"]["wikipedia"].get("selected", False), "Wikipedia tool should be selected for factual claims"


def test_tool_selection_reasoning():
    """Test that tool selection includes reasoning"""
    claim = "The Earth orbits the Sun"
    result = agent.invoke({"claim": claim})

    # Check that each tool selection includes reasoning
    for tool_name, selection in result["tool_selections"].items():
        assert "reasoning" in selection, f"Tool selection for {tool_name} should include reasoning"
        assert selection["reasoning"], f"Reasoning for {tool_name} should not be empty"


def test_mixed_claim():
    """Test behavior with a claim that might need multiple tools"""
    claim = "If you multiply the distance from Earth to the Sun (93 million miles) by 2, you get 186 million miles"
    result = agent.invoke({"claim": claim})

    # This claim might need both Wikipedia and calculator tools
    wikipedia_selected = result["tool_selections"].get("wikipedia", {}).get("selected", False)
    calculator_selected = any(
        result["tool_selections"].get(tool_name, {}).get("selected", False)
        for tool_name in ["multiply", "add", "divide"]
    )
    
    assert wikipedia_selected or calculator_selected, "At least one tool should be selected for mixed claims"
    
    # Check that the evidence matches the selected tools
    for evidence in result["evidence"]:
        tool_name = evidence["name"]
        assert result["tool_selections"].get(tool_name, {}).get("selected", False), f"Evidence uses tool {tool_name} which should be selected"
