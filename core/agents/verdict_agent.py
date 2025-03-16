from dotenv import load_dotenv
import json
import os
from langchain_core.messages import SystemMessage, BaseMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from typing import TypedDict

# Load environment variables
load_dotenv('.env', override=True)

# Define the LLM model to use
MODEL = "mistral-nemo"
TEMPERATURE = 0

llm = ChatOllama(
    model=MODEL,
    temperature=TEMPERATURE,
)

# Define the State Object
class State(TypedDict):
    messages: list[BaseMessage]
    claims: list[str]
    labels: list[str]
    justifications: list[str]
    final_label: str | None
    final_justification: str | None

# Nodes

def prompt_prep_node(state: State) -> State:
    with open("prompts/verdict_agent_system_prompt.txt", "r") as f:
        prompt_text = f.read()

    claim_analysis = "\n".join(
        [f"Claim: {state['claims'][i]}\nVerdict: {state['labels'][i]}\nJustification: {state['justifications'][i]}\n"
         for i in range(len(state["claims"]))]
    )

    formatted_prompt = prompt_text.format(
        claim_analysis=claim_analysis
    )

    messages = [SystemMessage(content=formatted_prompt)] + state["messages"]

    return {**state, "messages": messages}

def verdict_node(state: State) -> State:
    response = llm.invoke(state['messages'])
    return {**state, "messages": state["messages"] + [response]}

def postprocessing_node(state: State) -> State:
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
        **state,
        "messages": state["messages"] + [formatted_response],
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

