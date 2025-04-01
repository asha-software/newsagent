from dotenv import load_dotenv
import json
from pathlib import Path
from langchain_core.messages import SystemMessage, BaseMessage, AIMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing import Annotated, TypedDict, Dict

# Load environment variables
load_dotenv('.env', override=True)
LLM_OUTPUT_FORMAT = {
    "type": "object",
    "properties": {
        "final_label": {
            "type": "string",
            "enum": ["true", "false", "mixed", "unknown"]
        },
        "final_justification": {
            "type": "string"
        }
    },
    "required": ["final_label", "final_justification"]
}
BASE_DIR = Path(__file__).parent.resolve()
MODEL = "llama3"
TEMPERATURE = 0

llm = ChatOllama(model=MODEL, temperature=TEMPERATURE,
                 format=LLM_OUTPUT_FORMAT)


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    claims: list[str]
    labels: list[str]
    justifications: list[str]
    final_label: str | None
    final_justification: str | None


with open(BASE_DIR / "prompts/claim_decomposer_system_prompt.txt", "r") as f:
    system_prompt = f.read()
system_message = SystemMessage(content=system_prompt)


# Nodes definitions
def prompt_prep_node(state: State) -> dict:

    claim_analysis = "### Claims Analysis\n" + "\n".join(
        f"Claim: {state['claims'][i]}\nVerdict: {state['labels'][i]}\nJustification: {state['justifications'][i]}"
        for i in range(len(state["claims"]))
    )
    return {"messages": [system_message, AIMessage(content=claim_analysis)]}


def verdict_node(state: State) -> dict:
    response = llm.invoke(state['messages'])
    return {"messages": response}


def postprocessing_node(state: State) -> dict:
    response = state['messages'][-1]

    try:
        structured = json.loads(response.content)
    except json.JSONDecodeError as e:
        print("JSON decode error:", e)
        print("Raw response content:", response.content)

        structured = {
            "final_label": "unknown",
            "final_justification": "Model did not return valid JSON."
        }

    return {
        "final_label": structured.get("final_label", "Verdict Agent did not return a verdict."),
        "final_justification": structured.get("final_justification", "Verdict Agent did not return a justification."),
    }


# Graph definition
builder = StateGraph(State)

builder.add_node("prompt_prep", prompt_prep_node)
builder.add_node("verdict", verdict_node)
builder.add_node("postprocessing", postprocessing_node)

builder.add_edge(START, "prompt_prep")
builder.add_edge("prompt_prep", "verdict")
builder.add_edge("verdict", "postprocessing")
builder.add_edge("postprocessing", END)

verdict_agent = builder.compile()
