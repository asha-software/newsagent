from dotenv import load_dotenv
import json
import os
from pathlib import Path
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing import Annotated, Literal, TypedDict
from core.agents.utils.llm_factory import get_chat_model
from core.agents.utils.common_types import Evidence

DEFAULT_MODEL = "mistral-nemo"  # Default model to use if not specified in .env

# Absolute path to this dir. For relative paths like prompts
DIR = Path(__file__).parent.resolve()

# Load env variables from core/.env
load_dotenv(DIR.parent / ".env", override=True)


# Define agent state & LLM
class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    claim: str
    evidence: list[Evidence]
    label: Literal["true", "false", "unknown"] | None
    justification: str | None


LLM_OUTPUT_FORMAT = {
    "type": "object",
    "properties": {
        "label": {
            "type": "string",
            "enum": ["true", "false", "unknown"]
        },
        "justification": {
            "type": "string"
        }
    },
    "required": ["label", "justification"]
}

llm = get_chat_model(model_name=os.getenv(
    "REASONING_AGENT_MODEL", DEFAULT_MODEL), format_output=LLM_OUTPUT_FORMAT)

with open(DIR / "prompts/reasoning_agent_system_prompt.txt", "r") as f:
    system_prompt = f.read()

# Define agent graph nodes


def preprocessing(state: State) -> State:
    """
    Formats the system prompt template with the evidence, then supplies the claim
    as a human message. The working assumption is that putting the evidence in the
    system prompt will help make the model trust it more than the claim.
    """
    # Format system prmopt template: unwind the evidence list to a bullet list
    for ev in state["evidence"]:
        print(f"Evidence: {ev['name']}: {ev['content'][:20]}")
        print(f"{ev['args']}, {ev['source']}")
    evidence_str = "\n".join(
        [f"* {ev['name']}: {ev['content']}" for ev in state["evidence"]])
    formatted_prompt = system_prompt.format(evidence=evidence_str)

    # Set system and human messages in the state
    sys_message = SystemMessage(content=formatted_prompt)
    claim_message = HumanMessage(content='Claim: ' + state['claim'])

    return {'messages': [sys_message, claim_message]}


def assistant(state: State) -> State:

    response = llm.invoke(state['messages'])
    return {"messages": response}


def postprocessing(state: State) -> State:
    # TODO: reimplement in Pydantic/Langchain
    reasoning = state['messages'][-1].content

    try:
        # Try to parse the reasoning as JSON
        formatted_reasoning = json.loads(reasoning)
    except json.JSONDecodeError as e:
        print(f"JSONDecodeError: {e}")
        print(f"Reasoning content: {reasoning}")

    label = formatted_reasoning['label']
    justification = formatted_reasoning['justification']
    return {"label": label, "justification": justification}


# Build the graph
builder = StateGraph(State)
builder.add_node("preprocessing", preprocessing)
builder.add_node("assistant", assistant)
builder.add_node("postprocessing", postprocessing)

builder.add_edge(START, "preprocessing")
builder.add_edge("preprocessing", "assistant")

builder.add_edge("assistant", "postprocessing")
builder.add_edge("postprocessing", END)
reasoning_agent = builder.compile()
