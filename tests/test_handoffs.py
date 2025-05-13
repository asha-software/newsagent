import pytest, inspect
from core.pipeline import pipeline
from core.agents.claim_decomposer import claim_node
from core.agents.research_agent import research_node
from core.agents.reasoning_agent import reason_node

# 1. Graph has exactly the four wrapper nodes
def test_graph_structure():
    nodes = {n for n in pipeline.nodes if not n.startswith("__")}
    assert nodes == {"claim", "research", "reason", "verdict"}

# 2. Each wrapper uses Command
@pytest.mark.parametrize("func", [claim_node, research_node, reason_node])
def test_node_returns_command(func):
    src = inspect.getsource(func)
    assert "Command(" in src, f"{func.__name__} must return Command(...)"

# 3. Final output has no 'messages' and contains only the public keys
def test_pipeline_no_message_leak():
    result = pipeline.invoke({"text": "Sky is blue."})
    # must not contain any 'messages'
    def recurse(o):
        if isinstance(o, dict):
            assert "messages" not in o, f"Leaked messages in {o}"
            for v in o.values():
                recurse(v)
        elif isinstance(o, list):
            for i in o:
                recurse(i)
    recurse(result)
    # must have the final verdict keys
    assert "final_label" in result
    assert "final_justification" in result
    
# Expected update keys for each wrapper node
_expected = {
    "claim":       {"claims"},
    "research":    {"evidence"},
    "reason":      {"labels", "justifications"},
    "verdict":     {"final_label", "final_justification"},
}

def test_per_node_update_content_and_no_messages():
    """
    Stream the pipeline and for each node’s update:
    - assert no 'messages' key
    - assert the set of *new* keys includes what's expected
    """
    for step in pipeline.stream({"text": "Sky is blue."}):
        for node, upd in step.items():
            if node.startswith("__"):
                continue
            # 1) No messages
            assert "messages" not in upd, f"`{node}` leaked messages: {upd}"
            # 2) Must at least add its expected fields
            keys = set(upd.keys())
            assert _expected[node].issubset(keys), (
                f"`{node}` update missing expected keys { _expected[node] - keys }"
            )
