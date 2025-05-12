from dotenv import load_dotenv
import json
import os
from pathlib import Path
from langchain_core.messages import SystemMessage, BaseMessage, AIMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing import Annotated, TypedDict
from core.agents.utils.llm_factory import get_chat_model
from pydantic import BaseModel, Field

DEFAULT_MODEL = "mistral-nemo"  # Default model to use if not specified in .env

# Load environment variables
DIR = Path(__file__).parent.resolve()
load_dotenv(DIR.parent / ".env", override=True)


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


class ReasoningOutput(BaseModel):
    final_justification: str = Field(
        description="The final justification for the label assigned to the claim.")
    final_label: str = Field(
        description="The final label assigned to the claim.")


llm = get_chat_model(
    model_name=os.getenv("VERDICT_AGENT_MODEL", DEFAULT_MODEL),
    output_model=ReasoningOutput)


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    claims: list[str]
    labels: list[str]
    justifications: list[str]
    final_label: str | None
    final_justification: str | None


with open(DIR / "prompts/verdict_agent_system_prompt.txt", "r") as f:
    system_prompt = f.read()
system_message = SystemMessage(content=system_prompt)


# Nodes definitions

def prompt_prep_node(state: State) -> dict:
    claim_analysis = "### Claims Analysis\n\n"
    for i, (claim, label, justification) in enumerate(
        zip(state['claims'], state['labels'], state['justifications'])
    ):
        claim_analysis += f"Claim {i+1}:\n - Statement: {claim}\n - Verdict: {label}\n - Justification: {justification}\n\n"

    user_message_content = (
        f"{claim_analysis}"
        "Please apply the Guidelines and produce a single JSON response "
        "with `final_label` and `final_justification` for the entire document."
    )

    return {"messages": [system_message, HumanMessage(content=user_message_content)]}


def verdict_node(state: State) -> dict:
    response = llm.invoke(state['messages'])
    return {"final_label": response.final_label, "final_justification": response.final_justification}


# def postprocessing_node(state: State) -> dict:
#     response = state['messages'][-1]

#     try:
#         structured = json.loads(response.content)
#     except json.JSONDecodeError as e:
#         print("JSON decode error:", e)
#         print("Raw response content:", response.content)

#         structured = {
#             "final_label": "unknown",
#             "final_justification": "Model did not return valid JSON."
#         }

#     return {
#         "final_label": structured.get("final_label", "Verdict Agent did not return a verdict."),
#         "final_justification": structured.get("final_justification", "Verdict Agent did not return a justification."),
#     }

# Graph definition
builder = StateGraph(State)

builder.add_node("prompt_prep", prompt_prep_node)
builder.add_node("verdict", verdict_node)
# builder.add_node("postprocessing", postprocessing_node)

builder.add_edge(START, "prompt_prep")
builder.add_edge("prompt_prep", "verdict")
builder.add_edge("verdict", END)
# builder.add_edge("verdict", "postprocessing")
# builder.add_edge("postprocessing", END)

verdict_agent = builder.compile()


def main():
    # Example usage
    state = {
        "messages": [],
        "claims": ["I'm just a poor man from a poor family", "I am the walrus"],
        "labels": ["true", "false"],
        "justifications": ["My momma just killed a man", "I am the egg man, goo goo g'joob"],
        # "final_label": None,
        # "final_justification": None
    }
    result = verdict_agent.invoke(state)
    from pprint import pprint
    pprint(result)
    print(type(result))


if __name__ == "__main__":
    main()
