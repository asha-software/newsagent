from dotenv import load_dotenv
import os
from langchain.prompts import SystemMessagePromptTemplate
from langchain_core.messages import SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing import Annotated, TypedDict


MODEL = "mistral-nemo"
TEMPERATURE = 0
load_dotenv('.env', override=True)


class State(TypedDict):
    messages: Annotated[list[str], add_messages]
    claim: str
    evidence: list[str]

# Any tools needed?
# tools_in_use = []

llm = ChatOllama(
    model=MODEL, 
    temperature=TEMPERATURE,
    base_url="http://host.docker.internal:11434", # if running in the studio
    ).bind_tools(tools_in_use)

with open("prompts/reasoning_agent_system_prompt.txt", "r") as f:
    prompt_text = f.read()

"""
4. Define Nodes: functions taking state and returning state
"""
def prompt_prep_node(state: State) -> State:
    evidence_str = "\n".join([f"* {e}" for e in state["evidence"]])
    state['evidence_str'] = evidence_str
    return state

    
def reasoning_node(state: State) -> State:
    formatted_prompt = prompt_text.format(evidence=state["evidence_str"])

    # Prepend the system prompt to the messages list
    messages = [SystemMessage(content=formatted_prompt)] + state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}

"""
5. Build the graph
"""

builder = StateGraph(State)
builder.add_node("prompt_prep", prompt_prep_node)
builder.add_node("reasoning", reasoning_node)

builder.add_edge(START, "prompt_prep")
builder.add_edge("prompt_prep", "reasoning")
builder.add_edge("reasoning", END)
graph = builder.compile()


