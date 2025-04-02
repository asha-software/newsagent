from dotenv import load_dotenv
import json
from pathlib import Path
import sys
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing import Annotated, Literal, TypedDict

# Absolute path to this dir. For relative paths like prompts
BASE_DIR = Path(__file__).parent.resolve()

# Absolute path to repo root. This will be used to import Evidence from common_types
ROOT_DIR = BASE_DIR.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# fmt: off
from core.agents.common_types import Evidence
# fmt: on

MODEL = "mistral-nemo"
TEMPERATURE = 0
load_dotenv('.env', override=True)


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

llm = ChatOllama(
    model=MODEL,
    temperature=TEMPERATURE,
    format=LLM_OUTPUT_FORMAT,
    # base_url="http://host.docker.internal:11434"  # when running in Docker
)

"""
Define agent
"""
with open(BASE_DIR / "prompts/reasoning_agent_system_prompt.txt", "r") as f:
    system_prompt = f.read()


def preprocessing(state: State) -> State:
    """
    Formats the system prompt template with the evidence, then supplies the claim
    as a human message. The working assumption is that putting the evidence in the
    system prompt will help make the model trust it more than the claim.
    """
    # Format system prmopt template: unwind the evidence list to a bullet list
    evidence_str = "\n".join(
        [f"* {ev['name']}: {ev['result']}" for ev in state["evidence"]])
    formatted_prompt = system_prompt.format(evidence=evidence_str)

    # Set system and human messages in the state
    sys_message = SystemMessage(content=formatted_prompt)
    claim_message = HumanMessage(content='Claim: ' + state['claim'])

    return {'messages': [sys_message, claim_message]}


def assistant(state: State) -> State:

    response = llm.invoke(state['messages'])
    return {"messages": response}


def postprocessing(state: State) -> State:
    """
    #TODO: migrate the postprocessing logic to Pydantic/Langchain
    """
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


"""
Build the graph
"""
builder = StateGraph(State)
builder.add_node("preprocessing", preprocessing)
builder.add_node("assistant", assistant)
builder.add_node("postprocessing", postprocessing)

builder.add_edge(START, "preprocessing")
builder.add_edge("preprocessing", "assistant")

builder.add_edge("assistant", "postprocessing")
builder.add_edge("postprocessing", END)
reasoning_agent = builder.compile()
