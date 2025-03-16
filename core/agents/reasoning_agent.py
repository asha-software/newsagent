from dotenv import load_dotenv
import json
import os
from langchain.prompts import SystemMessagePromptTemplate
from langchain_core.messages import AIMessage, SystemMessage, BaseMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing import Annotated, NotRequired, TypedDict


MODEL = "mistral-nemo"
TEMPERATURE = 0
load_dotenv('.env', override=True)


class State(TypedDict):
    # messages: Annotated[list[str], add_messages]
    messages: list[BaseMessage]
    claim: str
    evidence: list[str]
    label: str | None
    justification: str | None

# Any tools needed?
# tools_in_use = []

llm = ChatOllama(
    model=MODEL, 
    temperature=TEMPERATURE,
    # base_url="http://host.docker.internal:11434", # if running in the studio
    )



"""
4. Define Nodes: functions taking state and returning state
"""
def prompt_prep_node(state: State) -> State:
    with open("prompts/reasoning_agent_system_prompt.txt", "r") as f:
        prompt_text = f.read()
    # Unwind the evidence list to a bullet list
    evidence_str = "\n".join([f"* {e}" for e in state["evidence"]])
    formatted_prompt = prompt_text.format(evidence=evidence_str)
    messages = [SystemMessage(content=formatted_prompt)] + state["messages"]

    return {"messages": messages}
    
def reasoning_node(state: State) -> State:
    response = llm.invoke(state['messages'])
    return {"messages": state['messages'] + [response]}

def postprocessing_node(state: State) -> State:
    """
    #TODO: migrate the postprocessing logic to Pydantic/Langchain
    """
    reasoning = state['messages'][-1].content
    prompt = """Format the response into a JSON object with the following keys:
        "label": "true" | "false" | "unknown"
        "justification": "Justification for the label (string)"
    """
    formatted_reasoning = llm.invoke(reasoning + '\n' + prompt)
    results = json.loads(formatted_reasoning.content)
    label = results['label']
    justification = results['justification']
    return {"messages": state['messages'] + [formatted_reasoning],
            "label": label,
            "justification": justification}


"""
5. Build the graph
"""

builder = StateGraph(State)
builder.add_node("prompt_prep", prompt_prep_node)
builder.add_node("reasoning", reasoning_node)
builder.add_node("postprocessing", postprocessing_node)

builder.add_edge(START, "prompt_prep")
builder.add_edge("prompt_prep", "reasoning")

builder.add_edge("reasoning", "postprocessing")
builder.add_edge("postprocessing", END)
reasoning_agent = builder.compile()



