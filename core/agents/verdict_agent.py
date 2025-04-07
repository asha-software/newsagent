import json
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Annotated, TypedDict

from langchain_core.messages import SystemMessage, BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from core.agents.utils.llm_factory import get_chat_model

# Load environment variables
DIR = Path(__file__).parent.resolve()
load_dotenv(DIR.parent / ".env", override=True)
assert "VERDICT_AGENT_MODEL" in os.environ, "Please set the VERDICT_AGENT_MODEL environment variable"

# Load external system prompt
with open(DIR / "prompts/verdict_agent_system_prompt.txt", "r") as f:
    system_prompt_text = f.read()
system_message = SystemMessage(content=system_prompt_text)

# Define LLM Output Format
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

llm = get_chat_model(
    model_name=os.getenv("VERDICT_AGENT_MODEL"),
    format_output=LLM_OUTPUT_FORMAT
)

# Verdict Agent State
class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    claims: list[str]
    labels: list[str]
    justifications: list[str]
    final_label: str | None
    final_justification: str | None

# Prompt Preparation Node
def prompt_prep_node(state: State) -> dict:
    claim_analysis = "### Claims Analysis\n\n"
    for i, (claim, label, justification) in enumerate(
        zip(state['claims'], state['labels'], state['justifications'])
    ):
        claim_analysis += f"Claim {i+1}:\n - Statement: {claim}\n - Verdict: {label}\n - Justification: {justification}\n\n"

    user_message_content = (
        f"{claim_analysis}"
        "Please apply the Evaluation Guidelines and produce a single JSON response "
        "with `final_label` and `final_justification` for the entire document."
    )

    return {"messages": [system_message, HumanMessage(content=user_message_content)]}

# Verdict Node
def verdict_node(state: State) -> dict:
    response = llm.invoke(state["messages"])
    return {"messages": state["messages"] + [response]}

# Postprocessing Node
def postprocessing_node(state: State) -> dict:
    response = state["messages"][-1]
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
        "final_justification": structured.get("final_justification", "Verdict Agent did not return a justification.")
    }

# Graph Definition
builder = StateGraph(State)
builder.add_node("prompt_prep", prompt_prep_node)
builder.add_node("verdict", verdict_node)
builder.add_node("postprocessing", postprocessing_node)

builder.add_edge(START, "prompt_prep")
builder.add_edge("prompt_prep", "verdict")
builder.add_edge("verdict", "postprocessing")
builder.add_edge("postprocessing", END)

verdict_agent = builder.compile()
q