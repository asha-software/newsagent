from typing import TypedDict, List
from langgraph.graph import StateGraph, START, END
from core.agents.claim_decomposer import claim_node
from core.agents.research_agent import research_node
from core.agents.reasoning_agent import reason_node
from core.agents.verdict_agent import verdict_node
from core.agents.utils.common_types import Evidence

# Define the shared pipeline state schema
class PipeState(TypedDict, total=False):
    text: str
    claims: List[str]
    evidence: List[List[Evidence]]
    labels: List[str]
    justifications: List[str]
    final_label: str
    final_justification: str

builder = StateGraph(PipeState)
builder.add_node("claim", claim_node)
builder.add_node("research", research_node)
builder.add_node("reason", reason_node)
builder.add_node("verdict", verdict_node)

builder.add_edge(START, "claim")
builder.add_edge("claim", "research")
builder.add_edge("research", "reason")
builder.add_edge("reason", "verdict")
builder.add_edge("verdict", END)

pipeline = builder.compile()
