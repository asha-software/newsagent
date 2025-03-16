
from dotenv import load_dotenv
import json
import os
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing import Annotated, TypedDict


MODEL = "mistral-nemo"
TEMPERATURE = 0
load_dotenv('.env', override=True)

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

llm = ChatOllama(
    model=MODEL,
    temperature=TEMPERATURE,
    format=LLM_OUTPUT_FORMAT
)

"""
Build the graph
"""

with open("prompts/claim_decomposer_system_prompt.txt", "r") as f:
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
