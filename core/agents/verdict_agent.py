from dotenv import load_dotenv
import json
import os
from langchain_core.messages import SystemMessage, BaseMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing import Annotated, TypedDict

# Load environment variables
load_dotenv('.env', override=True)

# LLM Model
MODEL = "mistral-nemo"
TEMPERATURE = 0

llm = ChatOllama(model=MODEL, temperature=TEMPERATURE)

# State Object with explicit reducer
class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    claims: list[str]
    labels: list[str]
    justifications: list[str]
    final_label: str | None
    final_justification: str | None

# Nodes definitions

def prompt_prep_node(state: State) -> dict:
    with open("prompts/verdict_agent_system_prompt.txt", "r") as f:
        prompt_text = f.read()

    claim_analysis = "\n".join(
        f"Claim: {state['claims'][i]}\nVerdict: {state['labels'][i]}\nJustification: {state['justifications'][i]}"
        for i in range(len(state["claims"]))
    )

    formatted_prompt = prompt_text.format(claim_analysis=claim_analysis)

    # Return ONLY new messages
    return {"messages": [SystemMessage(content=formatted_prompt)]}

def verdict_node(state: State) -> dict:
    response = llm.invoke(state['messages'])
    # Return only newly generated message
    return {"messages": [response]}

def postprocessing_node(state: State) -> dict:
    response_text = state["messages"][-1].content
    prompt = """Format the response into a JSON object with the following keys:
{
  "final_label": "true" | "false" | "mixed" | "unknown",
  "final_justification": "A summary of why this document is classified this way."
}
Respond ONLY with the JSON object. No additional text.
"""

    formatted_response = llm.invoke(response_text + '\n' + prompt)

    try:
        results = json.loads(formatted_response.content)
    except json.JSONDecodeError:
        results = {
            "final_label": "unknown",
            "final_justification": "LLM response could not be parsed as JSON."
        }

    return {
        "messages": [formatted_response],  # Only new message
        "final_label": results["final_label"],
        "final_justification": results["final_justification"]
    }

# Graph
builder = StateGraph(State)

builder.add_node("prompt_prep", prompt_prep_node)
builder.add_node("verdict", verdict_node)
builder.add_node("postprocessing", postprocessing_node)

builder.add_edge(START, "prompt_prep")
builder.add_edge("prompt_prep", "verdict")
builder.add_edge("verdict", "postprocessing")
builder.add_edge("postprocessing", END)

graph = builder.compile()
