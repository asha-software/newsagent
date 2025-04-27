from dotenv import load_dotenv
import os
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing import Annotated, TypedDict


MODEL = "mistral-nemo"
TEMPERATURE = 0
load_dotenv(".env", override=True)

"""
1. Define your State object
"""


class State(TypedDict):
    messages: Annotated[list[str], add_messages]
    # additional keys and their value types...


"""
2. Define your Tools: fully annotated functions of any kind
"""


def multiply(a: int, b: int) -> int:
    """Multiply `a` and `b`

    Args:
        a: First number
        b: Second number
    """
    return a * b


tools_in_use = [multiply]

""" 
3. Instantiate your llm (Ollama or other) and bind the tools to it
"""
llm = ChatOllama(
    model=MODEL,
    temperature=TEMPERATURE,
    base_url="http://host.docker.internal:11434",  # if running in the studio
).bind_tools(tools_in_use)

"""
4. Define Nodes: functions taking state and returning state
"""


def node_a(state: State) -> State:
    # do something with state
    print("=== node_a ===")
    response = llm.invoke(state["messages"])

    # Here we return an object following the State type;
    # by annotating `add_message`, the new response will be appended
    # to the messages list and assigned an id
    return {"messages": [response]}


"""
5. Build the graph
"""

builder = StateGraph(State)
builder.add_node("node_a", node_a)
builder.add_node("tools", ToolNode(tools_in_use))

builder.add_conditional_edges("node_a", tools_condition)
builder.add_edge(START, "node_a")
builder.add_edge("tools", END)
graph = builder.compile()
