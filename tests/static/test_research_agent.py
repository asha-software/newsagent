import pytest
import importlib
import unittest.mock
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

###############################
# Fixtures and Test Helpers
###############################


def dummy_tool_function(query: str) -> str:
    """Example docstring for dummy_tool_function."""
    return f"Dummy result for {query}"


@pytest.fixture()
def mock_module():
    return unittest.mock.MagicMock()


@pytest.fixture()
def research_agent_uut(monkeypatch):
    monkeypatch.setenv("RESEARCH_AGENT_MODEL", "mistral:7b")
    import core.agents.research_agent as research_agent

    return research_agent


@pytest.fixture
def mock_import_module_success(mock_module):
    """
    Patch importlib.import_module to simulate a successful import
    returning a module with `tool_function = dummy_tool_function`.
    """
    with unittest.mock.patch.object(importlib, "import_module") as mock_import:
        mock_module.tool_function = dummy_tool_function
        mock_import.return_value = mock_module
        yield mock_import


@pytest.fixture
def mock_import_module_no_toolfunc(mock_module):
    """
    Patch importlib.import_module to simulate a module with no `tool_function`.
    """
    with unittest.mock.patch.object(importlib, "import_module") as mock_import:
        if hasattr(mock_module, "tool_function"):
            del mock_module.tool_function
        mock_import.return_value = mock_module
        yield mock_import


@pytest.fixture
def mock_import_module_failure():
    """Patch importlib.import_module to simulate a failed import."""
    with unittest.mock.patch.object(importlib, "import_module") as mock_import:
        mock_import.side_effect = ImportError("Module not found")
        yield mock_import


@pytest.fixture
def mock_llm(mock_module):
    """
    A fixture to mock the LLM object with .bind_tools() returning itself
    and invoke() returning a simple structure.
    """
    mock_llm_obj = mock_module
    mock_llm_obj.bind_tools.return_value = mock_llm_obj
    mock_llm_obj.invoke.return_value = [mock_module, mock_module]
    return mock_llm_obj


@pytest.fixture
def mock_import_module_forced_attr_error(mock_module):
    """
    Patch importlib.import_module to succeed, but getattr() to raise AttributeError
    AFTER successful import.
    """
    original_getattr = getattr

    def custom_getattr(obj, name):
        if name == "tool_function":
            raise AttributeError("Forced attribute error for test.")
        return original_getattr(obj, name)

    with unittest.mock.patch.object(importlib, "import_module") as mock_import:
        mock_import.return_value = mock_module
        with unittest.mock.patch("builtins.getattr", side_effect=custom_getattr):
            yield mock_import


@pytest.fixture
def multiple_tool_calls_state():
    """
    Returns a state with multiple AIMessage tool calls and matching ToolMessages.
    """
    return {
        "messages": [
            AIMessage(
                content="Tool calls here.",
                tool_calls=[
                    {"id": "toolcall1", "name": "tool_one", "args": {"key": "val"}},
                    {"id": "toolcall2", "name": "tool_two", "args": {"foo": "bar"}},
                ],
            ),
            ToolMessage(content="Result from tool_one", tool_call_id="toolcall1"),
            HumanMessage(content="User message in between."),
            ToolMessage(content="Result from tool_two", tool_call_id="toolcall2"),
        ],
        "claim": "Multiple tool calls with multiple matches",
        "evidence": [],
    }


@pytest.fixture
def empty_state():
    """Returns a state with no messages."""
    return {"messages": [], "claim": "Some claim", "evidence": []}


@pytest.fixture
def no_tool_calls_state():
    """Returns a state where AIMessage has no tool_calls."""
    return {
        "messages": [
            AIMessage(
                content="Hello, I am just a normal AIMessage with no tools.",
                tool_calls=[],
            ),
            HumanMessage(content="User message here."),
        ],
        "claim": "No tool calls claim",
        "evidence": [],
    }


@pytest.fixture
def single_tool_call_no_tool_message_state():
    """
    Returns a state where AIMessage has a tool call but
    there is no matching ToolMessage.
    """
    return {
        "messages": [
            AIMessage(
                content="I might use a tool.",
                tool_calls=[
                    {
                        "id": "toolcall1",
                        "name": "some_tool",
                        "args": {"param1": "value1"},
                    }
                ],
            ),
            HumanMessage(content="User message here."),
        ],
        "claim": "Single tool call, no matching ToolMessage",
        "evidence": [],
    }


@pytest.fixture
def single_tool_call_with_tool_message_state():
    """
    Returns a state with a single AIMessage tool call and a matching ToolMessage.
    """
    return {
        "messages": [
            AIMessage(
                content="I'm using a tool now.",
                tool_calls=[
                    {"id": "toolcall1", "name": "some_tool", "args": {"param": "val"}}
                ],
            ),
            ToolMessage(content="Tool result content", tool_call_id="toolcall1"),
            HumanMessage(content="User message after tool."),
        ],
        "claim": "Single tool call with matching ToolMessage",
        "evidence": [],
    }


###############################
# Tests for `import_builtin`
###############################
class TestImportBuiltin:
    def test_import_builtin_success(
        self, mock_import_module_success, research_agent_uut
    ):
        """
        Should return the function if the module and function exist.
        """
        module_name = "my_module"
        tool_func = research_agent_uut.import_builtin(module_name)
        assert tool_func is dummy_tool_function
        assert callable(tool_func)
        assert tool_func.__name__ == "dummy_tool_function"

    def test_import_builtin_no_function(
        self, mock_import_module_no_toolfunc, research_agent_uut
    ):
        """
        Return None if the module is imported but no `tool_function` attribute exists.
        """
        module_name = "module_without_tool_function"
        tool_func = research_agent_uut.import_builtin(module_name)
        assert tool_func is None

    def test_import_builtin_failure(
        self, mock_import_module_failure, research_agent_uut
    ):
        """
        Return None if the module doesn't exist.
        """
        module_name = "non_existent_module"
        tool_func = research_agent_uut.import_builtin(module_name)
        assert tool_func is None

    def test_import_builtin_importerror(self, research_agent_uut):
        """
        Forces an ImportError by attempting to import a non-existent module.
        """
        with unittest.mock.patch.object(
            importlib, "import_module", side_effect=ImportError("No module")
        ):
            result = research_agent_uut.import_builtin("does_not_exist")
        assert result is None

    def test_import_builtin_attributerror(self, research_agent_uut):
        """
        Forces an AttributeError by mocking a module that doesn't have `tool_function`.
        """
        with unittest.mock.patch.object(
            importlib,
            "import_module",
            return_value=unittest.mock.MagicMock(spec=[]),
        ):
            result = research_agent_uut.import_builtin("exists_but_no_tool_function")
        assert result is None

    def test_import_builtin_exceptionerror(self, research_agent_uut):
        """
        Forces an Exception.
        """
        with unittest.mock.patch.object(
            importlib, "import_module", side_effect=Exception("No module")
        ):
            result = research_agent_uut.import_builtin("does_not_exist")
        assert result is None

    def test_import_builtin_has_success(self, research_agent_uut, mock_module):
        """
        Covers the normal success path.
        """
        mock_module.tool_function = dummy_tool_function
        with unittest.mock.patch.object(
            importlib, "import_module", return_value=mock_module
        ):
            result = research_agent_uut.import_builtin("some_module")
        assert result is dummy_tool_function
        assert callable(result)


###############################
# Tests for `render_user_defined_tools`
###############################
class TestRenderUserDefinedTools:

    def test_render_user_defined_tools_empty(self, research_agent_uut):
        """
        Return empty list for an empty tool_kwargs list.
        """
        tool_kwargs_list = []
        results = research_agent_uut.render_user_defined_tools(tool_kwargs_list)
        assert results == []

    def test_render_user_defined_tools_success(self, research_agent_uut):
        """
        Tests providing a non-empty tool_kwargs list where create_tool(...) succeeds for each item.
        """
        # Mock create_tool so it does not raise Exception
        with unittest.mock.patch(
            "core.agents.research_agent.create_tool"
        ) as mock_create_tool:
            dummy_tool = unittest.mock.MagicMock()
            mock_create_tool.return_value = dummy_tool
            # Provide a single tool definition
            tool_kwargs_list = [
                {"name": "test_tool", "method": "GET", "url_template": "http://test"}
            ]
            # Act
            tools = research_agent_uut.render_user_defined_tools(tool_kwargs_list)
            # Assert
            assert len(tools) == 1
            assert tools[0] is dummy_tool
            mock_create_tool.assert_called_once_with(**tool_kwargs_list[0])

    def test_render_user_defined_tools_failure(self, research_agent_uut, capsys):
        """
        Tests whenn create_tool(...) raises an Exception
        """
        # Mock create_tool so it raises an Exception
        with unittest.mock.patch(
            "core.agents.research_agent.create_tool"
        ) as mock_create_tool:
            mock_create_tool.side_effect = Exception("Test error: create_tool failed")
            # Provide a single tool definition
            tool_kwargs_list = [
                {"name": "test_tool", "method": "GET", "url_template": "http://test"}
            ]

            # Act
            tools = research_agent_uut.render_user_defined_tools(tool_kwargs_list)

            # Assert
            assert len(tools) == 0
            mock_create_tool.assert_called_once_with(**tool_kwargs_list[0])

            # Check that the exception message was printed
            captured = capsys.readouterr()
            assert "Error creating tool with kwargs" in captured.out
            assert "Test error: create_tool failed" in captured.out


###############################
# Tests for `create_agent`
###############################
class TestCreateAgent:
    def test_create_agent_no_model(self, research_agent_uut, mock_module):
        with unittest.mock.patch(
            "core.agents.research_agent.get_chat_model"
        ) as mock_get_chat_model:
            mock_llm = mock_module
            mock_llm.bind_tools.return_value = mock_llm
            mock_get_chat_model.return_value = mock_llm
            agent_graph = research_agent_uut.create_agent(
                model=None, builtin_tools={}, user_tool_kwargs=[]
            )
        mock_get_chat_model.assert_called_once_with(model_name="mistral:7b")
        assert agent_graph is not None

    def test_create_agent_full_flow_no_tool_calls(
        self, research_agent_uut, mock_module
    ):
        """
        Mock LLM that returns an AIMessage with zero tool calls
        and verify we produce no evidence.
        """
        mock_llm = mock_module
        mock_llm.bind_tools.return_value = mock_llm
        ai_message_no_tool = AIMessage(content="I do not need any tools", tool_calls=[])
        mock_llm.invoke.return_value = [ai_message_no_tool]

        with unittest.mock.patch(
            "core.agents.research_agent.get_chat_model"
        ) as mock_get_chat_model:
            mock_get_chat_model.return_value = mock_llm
            agent = research_agent_uut.create_agent(
                model="mistral-nemo", builtin_tools={}, user_tool_kwargs=[]
            )

        final_state = agent.invoke({"claim": "Another claim"})
        assert final_state is not None
        assert "messages" in final_state
        assert final_state.get("evidence") == [], "Expected empty evidence"


###############################
# Tests for `postprocessing`
###############################
class TestStatePostProcessing:
    def test_post_processing_empty_state(self, research_agent_uut, empty_state):
        """
        No messages in the state -> evidence remains empty.
        """
        result = research_agent_uut.gather_evidence(empty_state)
        assert result["evidence"] == [], "Expected no evidence when state is empty."

    def test_post_processing_no_tool_calls(
        self, research_agent_uut, no_tool_calls_state
    ):
        """
        AIMessage present but 'tool_calls' is empty -> evidence remains empty.
        """
        result = research_agent_uut.gather_evidence(no_tool_calls_state)
        assert (
            result["evidence"] == []
        ), "Expected no evidence when AIMessage has no tool_calls."

    def test_post_processing_single_tool_call_no_tool_message(
        self, research_agent_uut, single_tool_call_no_tool_message_state
    ):
        """
        AIMessage has tool_calls, but no matching ToolMessage -> no evidence is collected.
        """
        result = research_agent_uut.gather_evidence(
            single_tool_call_no_tool_message_state
        )
        assert (
            result["evidence"] == []
        ), "Expected no evidence when the tool_call has no matching ToolMessage."

    def test_post_processing_single_tool_call_with_tool_message(
        self, research_agent_uut, single_tool_call_with_tool_message_state
    ):
        """
        AIMessage has a single tool_call and exactly one matching ToolMessage ->
        that single piece of evidence is collected.
        """
        result = research_agent_uut.gather_evidence(
            single_tool_call_with_tool_message_state
        )
        assert len(result["evidence"]) == 1, "Expected exactly one evidence item."
        evidence_item = result["evidence"][0]
        assert evidence_item["name"] == "some_tool"
        assert evidence_item["args"] == {"param": "val"}
        assert evidence_item["result"] == "Tool result content"

    def test_post_processing_multiple_tool_calls(
        self, research_agent_uut, multiple_tool_calls_state
    ):
        """
        AIMessage has multiple tool_calls.
        Each tool_call has a matching ToolMessage somewhere in the later messages.
        We break after the first match for each tool_call.
        """
        result = research_agent_uut.gather_evidence(multiple_tool_calls_state)
        # We expect exactly two evidence items, one for each tool_call.
        assert len(result["evidence"]) == 2, "Expected two evidence items."

        # The order should correspond to the order of tool_calls in the AIMessage
        first_call = result["evidence"][0]
        assert first_call["name"] == "tool_one"
        assert first_call["args"] == {"key": "val"}
        assert first_call["result"] == "Result from tool_one"

        second_call = result["evidence"][1]
        assert second_call["name"] == "tool_two"
        assert second_call["args"] == {"foo": "bar"}
        assert second_call["result"] == "Result from tool_two"
