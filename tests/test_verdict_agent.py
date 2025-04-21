from langchain_ollama import ChatOllama
import pytest
from unittest.mock import patch
import json
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


@pytest.fixture()
def verdict_agent_uut(monkeypatch):
    monkeypatch.setenv("VERDICT_AGENT_MODEL", "mistral:7b")
    import core.agents.verdict_agent as verdict_agent

    return verdict_agent


@pytest.mark.usefixtures("verdict_agent_uut")
class TestVerdictAgentNodes:
    @pytest.fixture
    def sample_state(self):
        """
        Returns a sample State-like dictionary to be used in tests.
        """
        return {
            "messages": [],
            "claims": ["Claim one text", "Claim two text"],
            "labels": ["true", "false"],
            "justifications": ["Because it is correct", "Because it is incorrect"],
            "final_label": None,
            "final_justification": None,
        }

    def test_prompt_prep_node_basic(self, verdict_agent_uut, sample_state):
        """
        Test that prompt_prep_node returns a dict with:
          - A list containing SystemMessage and a HumanMessage
          - The HumanMessage content includes the expected claims analysis text
        """
        # Extract the function to test from the verdict agent code
        prompt_prep_node = verdict_agent_uut.prompt_prep_node
        result = prompt_prep_node(sample_state)
        assert "messages" in result
        # The first message should be the system message
        assert isinstance(result["messages"][0], SystemMessage)
        # The second message should be the constructed user/human message
        assert isinstance(result["messages"][1], HumanMessage)
        human_content = result["messages"][1].content
        assert "Claim 1:" in human_content
        assert "Claim 2:" in human_content

    @pytest.mark.parametrize(
        "claims, labels, justifications",
        [
            ([], [], []),
            (["Single claim"], ["unknown"], ["Could not verify"]),
        ],
    )
    def test_prompt_prep_node_various_inputs(
        self, verdict_agent_uut, claims, labels, justifications
    ):
        """
        Test prompt_prep_node with different claim/label/justification lengths,
        including edge cases like empty claims.
        """
        prompt_prep_node = verdict_agent_uut.prompt_prep_node

        state = {
            "messages": [],
            "claims": claims,
            "labels": labels,
            "justifications": justifications,
            "final_label": None,
            "final_justification": None,
        }
        result = prompt_prep_node(state)
        assert "messages" in result

        # Check the HumanMessage content
        if claims:
            human_content = result["messages"][1].content
            # For each claim, verify it appears in the prompt
            for i, claim in enumerate(claims):
                assert f"Claim {i+1}:" in human_content
                assert claim in human_content
        else:
            # If no claims, the prompt should still mention "Claims Analysis" but no claim lines
            human_content = result["messages"][1].content
            assert "Claims Analysis" in human_content
            assert "Claim 1:" not in human_content

    @pytest.fixture
    def sample_messages(self):
        """Creates a sample 'messages' list for feeding into verdict_node or postprocessing_node."""
        return [
            SystemMessage(content="System prompt"),
            HumanMessage(content="User prompt"),
        ]

    @pytest.fixture
    def fake_llm_response(self):
        """Return an AIMessage that resembles a typical LLM response with JSON content."""
        json_content = {
            "final_label": "true",
            "final_justification": "After evaluating all claims, I conclude it is true.",
        }
        return AIMessage(content=json.dumps(json_content))

    def test_verdict_node_invokes_llm(
        self, verdict_agent_uut, sample_state, sample_messages, fake_llm_response
    ):
        """
        Test that verdict_node calls llm.invoke(...) with the state's messages
        and returns a dict containing 'messages' with the LLM response appended.
        """
        verdict_node = verdict_agent_uut.verdict_node

        # We replace the actual llm with a mock
        with patch.object(
            ChatOllama, "invoke", return_value=[fake_llm_response]
        ) as mock_invoke:
            # Provide the state with some messages
            test_state = sample_state.copy()
            test_state["messages"] = sample_messages

            result = verdict_node(test_state)
            mock_invoke.assert_called_once_with(sample_messages)

            # result should be a dict with "messages" that is the LLM's return_value
            assert "messages" in result
            assert result["messages"] == [fake_llm_response]

    def test_postprocessing_node_valid_json(self, verdict_agent_uut):
        """
        Test postprocessing_node with a valid JSON in the last message.
        It should successfully parse 'final_label' and 'final_justification'.
        """
        postprocessing_node = verdict_agent_uut.postprocessing_node

        valid_json_message = AIMessage(
            content=json.dumps(
                {
                    "final_label": "true",
                    "final_justification": "All statements check out.",
                }
            )
        )

        state = {
            "messages": [valid_json_message],
            "claims": [],
            "labels": [],
            "justifications": [],
            "final_label": None,
            "final_justification": None,
        }

        result = postprocessing_node(state)
        assert "final_label" in result
        assert "final_justification" in result
        assert result["final_label"] == "true"
        assert result["final_justification"] == "All statements check out."

    def test_postprocessing_node_invalid_json(self, verdict_agent_uut):
        """
        Test postprocessing_node with a malformed JSON in the last message.
        Should fall back to "unknown" and a default error justification.
        """
        postprocessing_node = verdict_agent_uut.postprocessing_node

        invalid_json_message = AIMessage(content="This is not valid JSON")
        state = {
            "messages": [invalid_json_message],
            "claims": [],
            "labels": [],
            "justifications": [],
            "final_label": None,
            "final_justification": None,
        }

        result = postprocessing_node(state)
        assert result["final_label"] == "unknown"
        assert "Model did not return valid JSON" in result["final_justification"]

    def test_postprocessing_node_missing_keys(self, verdict_agent_uut):
        """
        Test postprocessing_node with partial JSON that doesn't include both
        'final_label' and 'final_justification'.
        The node should fall back to default strings where keys are missing.
        """
        postprocessing_node = verdict_agent_uut.postprocessing_node

        partial_json_message = AIMessage(
            content=json.dumps(
                {
                    "final_label": "mixed"
                    # 'final_justification' is missing
                }
            )
        )
        state = {
            "messages": [partial_json_message],
            "claims": [],
            "labels": [],
            "justifications": [],
            "final_label": None,
            "final_justification": None,
        }

        result = postprocessing_node(state)
        assert result["final_label"] == "mixed"
        assert (
            result["final_justification"]
            == "Verdict Agent did not return a justification."
        )
