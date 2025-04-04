
from dotenv import load_dotenv
import json
import os
from pathlib import Path
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing import Annotated, TypedDict
from core.agents.utils.llm_factory import get_chat_model

DIR = Path(__file__).parent.resolve()
# MODEL = "mistral-nemo"
# TEMPERATURE = 0

# Load env variables from core/.env
load_dotenv(DIR.parent / ".env", override=True)
assert "CLAIM_DECOMPOSER_MODEL" in os.environ, "Please set the CLAIM_DECOMPOSER_MODEL environment variable"

"""
Define State, LLM output schema, and LLM
"""


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    text: str
    claims: list[str]


LLM_OUTPUT_FORMAT = {
    "type": "array",
    "items": {
        "type": "string"
    }
}


llm = get_chat_model(
    model_name=os.getenv("CLAIM_DECOMPOSER_MODEL"),
    format_output=LLM_OUTPUT_FORMAT,
)


"""
Build the graph
"""

with open(DIR / "prompts/claim_decomposer_system_prompt.txt", "r") as f:
    system_prompt = f.read()
system_message = SystemMessage(content=system_prompt)


def preprocessing(state: State) -> State:
    """
    Preprocesses state before sending to the assistant for decomposition.
    Currently, this just extracts the text from the state, and sets it
    as a HumanMessage following the SystemMessage
    """
    state['messages'] = [system_message, HumanMessage(content=state['text'])]
    return state


def assistant(state: State) -> State:
    """
    Gets the LLM response to System and Human prompt
    """
    response = llm.invoke(state['messages'])
    return {'messages': response}


def postprocessing(state: State) -> State:
    """
    Postprocesses the LLM response to extract the claims
    Using format output on the LLM, we expect the AIMessage.content to be parsable
    as a list of strings
    """
    # We assume the last message in the state is the AI response
    message = state['messages'][-1]
    assert isinstance(
        message, AIMessage), "Postprocessing node expected the last message to be an AIMessage"
    try:
        claims = json.loads(message.content)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from claim decomposer: {e}")

    return {'claims': claims}


builder = StateGraph(State)

# Define nodes
builder.add_node("preprocessing", preprocessing)
builder.add_node("assistant", assistant)
builder.add_node("postprocessing", postprocessing)

# Define edges
builder.add_edge(START, "preprocessing")
builder.add_edge("preprocessing", "assistant")
builder.add_edge("assistant", "postprocessing")
builder.add_edge("postprocessing", END)

claim_decomposer = builder.compile()


def main():
    # Example usage
    initial_state = {"text": "The sky is blue and the grass is green."}
    result = claim_decomposer.invoke(initial_state)
    print(f"Decomposed claims: {result['claims']}")


if __name__ == "__main__":
    main()
