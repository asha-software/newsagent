# Project root added to pythonpath in pyproject.toml, allowing this import:
from tests.test_data.research_agent_test_cases import TOOL_USAGE_TEST_CASES


# def test_import():
#     assert agent is not None, "Agent should be imported successfully"
#
#
# def test_agent_processes_claim():
#     """Test that the agent can process a simple claim"""
#     claim = "Python was created by Guido van Rossum"
#     final_state = agent.invoke({"claim": claim})
#
#     print(f"Final evidence: {final_state['evidence']}")
#     print()
#     assert len(final_state["messages"]
#                ) >= 3, "Final state should have at least 3 messages: System, Human (claim) and AI (research agent response to claim)"
#     assert len(final_state["evidence"]
#                ) > 0, "Final state should contain evidence"
#
#
# @pytest.mark.parametrize("test_case", TOOL_USAGE_TEST_CASES)
# def test_tool_use(test_case):
#     """Parameterized test for tool usage with different claims"""
#     claim = test_case["claim"]
#     expected_tools = set(test_case["expected_tools"])
#     description = test_case["description"]
#
#     final_state = agent.invoke(
#         {"claim": claim, "messages": [], "evidence": []})
#     tools_used = {evidence["name"] for evidence in final_state["evidence"]}
#
#     # Check if the expected tools were used in evidence
#     formatted_description = description.format(
#         expected_tools=expected_tools,
#         tools_used=tools_used
#     )
#     assert expected_tools == tools_used, formatted_description


# test_research_agent.py
import pytest
import importlib
from unittest.mock import patch, MagicMock

# Import the module under test
# Adjust these imports to your actual module path if needed.
import os
os.environ["RESEARCH_AGENT_MODEL"] = "mistral:7b"

from core.agents import research_agent


@pytest.fixture
def mock_import_module_success():
    """
    Fixture to patch importlib.import_module to simulate a successful import.
    """
    with patch.object(importlib, 'import_module') as mock_import:
        # Create a mock module that has tool_function
        mock_module = MagicMock()
        mock_module.tool_function = MagicMock(return_value="mock_tool_function")
        mock_import.return_value = mock_module
        yield mock_import


@pytest.fixture
def mock_import_module_failure():
    """
    Fixture to patch importlib.import_module to simulate a failed import.
    """
    with patch.object(importlib, 'import_module') as mock_import:
        mock_import.side_effect = ImportError("Module not found")
        yield mock_import


def test_import_builtin_success(mock_import_module_success):
    """
    Test that import_builtin returns the function if the module and function exist.
    """
    module_name = "my_module"
    function = research_agent.import_builtin(module_name)
    assert function is not None
    assert callable(function)


def test_import_builtin_failure(mock_import_module_failure):
    """
    Test that import_builtin returns None if the module doesn't exist.
    """
    module_name = "non_existent_module"
    function = research_agent.import_builtin(module_name)
    assert function is None


@patch("research_agent.create_tool")
def test_render_user_defined_tools_success(mock_create_tool):
    """
    Test that render_user_defined_tools successfully creates a list of tools.
    """
    # Setup mock to return something for each create_tool
    mock_create_tool.return_value = MagicMock(name="MockTool")
    tool_kwargs_list = [
        {
            'name': 'tool1',
            'method': 'GET',
            'url_template': 'http://example.com/{param}',
            'param_mapping': {'param': {'type': 'str', 'for': 'url_params'}}
        },
        {
            'name': 'tool2',
            'method': 'POST',
            'url_template': 'http://example.org',
            'param_mapping': {}
        }
    ]
    tools = research_agent.render_user_defined_tools(tool_kwargs_list)

    # We expect two tools
    assert len(tools) == 2
    # Ensure the create_tool was called for each
    assert mock_create_tool.call_count == 2


@patch("research_agent.create_tool", side_effect=Exception("Error creating tool"))
def test_render_user_defined_tools_failure():
    """
    Test that render_user_defined_tools handles errors gracefully.
    """
    tool_kwargs_list = [
        {
            'name': 'invalid_tool',
            'method': 'GET',
        }
    ]
    # Should catch the exception internally and continue
    tools = research_agent.render_user_defined_tools(tool_kwargs_list)
    # The function will print the error and return an empty list item for the failing tool
    # The final returned list is either partial or empty depending on how your function
    # is written. By default code, it just logs the error, so no tools come out.
    assert len(tools) == 0


@patch("research_agent.get_chat_model")
@patch("research_agent.render_user_defined_tools")
@patch("research_agent.import_builtin")
def test_create_agent_success(mock_import_builtin, mock_render_user_defined_tools, mock_get_chat_model):
    """
    Test that create_agent returns a StateGraph with the expected structure.
    """
    # Mock the tool function from builtin
    mock_import_builtin.return_value = lambda: "builtin_tool"
    # Mock user-defined tools
    mock_render_user_defined_tools.return_value = ["user_tool_1", "user_tool_2"]
    # Mock the chat model's bind_tools
    mock_llm = MagicMock()
    mock_llm.invoke = MagicMock()
    mock_get_chat_model.return_value = MagicMock(bind_tools=MagicMock(return_value=mock_llm))

    # Build the agent
    builtin_tools = {'wikipedia': 'query', 'web_search': 'search'}
    user_tools = [{'name': 'tool1'}]  # Minimal example

    agent_graph = research_agent.create_agent(
        model='test-model',
        builtin_tools=builtin_tools,
        user_tool_kwargs=user_tools
    )
    assert agent_graph is not None

    # The final agent is a StateGraph instance
    # We can do some sanity checks on the node names or edges:
    nodes = agent_graph._graph.nodes()
    assert "preprocessing" in nodes
    assert "assistant" in nodes
    assert "tools" in nodes
    assert "postprocessing" in nodes

    edges = agent_graph._graph.edges()
    # Check some edges
    assert ("__start__", "preprocessing") in edges
    assert ("preprocessing", "assistant") in edges

    # Make sure the tool import was called for each builtin tool
    assert mock_import_builtin.call_count == len(builtin_tools)
    # Make sure user-defined tools were rendered
    assert mock_render_user_defined_tools.call_count == 1
    # Make sure the chat model was created
    mock_get_chat_model.assert_called_once()

