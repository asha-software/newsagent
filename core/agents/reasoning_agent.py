from dotenv import load_dotenv
import json
import os
from pathlib import Path
from langchain.prompts import SystemMessagePromptTemplate
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing import Annotated, Literal, TypedDict

BASE_DIR = Path(__file__).parent.resolve()
MODEL = "mistral-nemo"
TEMPERATURE = 0
load_dotenv('.env', override=True)


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    claim: str
    evidence: list[str]
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
    # base_url="http://host.docker.internal:11434", # if running in the studio
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
    evidence_str = "\n".join([f"* {e}" for e in state["evidence"]])
    formatted_prompt = system_prompt.format(evidence=evidence_str)

    # Set system and human messages in the state
    state['messages'] = [SystemMessage(content=formatted_prompt)]
    return {'messages': HumanMessage(content=state['claim'])}


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
