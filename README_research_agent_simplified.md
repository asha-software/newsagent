# Simplified Research Agent

This implementation of the research agent simplifies the approach based on feedback received. It leverages LangChain/LangGraph's built-in tool calling logic while still tracking which tools are used and collecting evidence.

## Key Differences from Previous Approaches

### Original Approach (`research_agent.py`):
- Used LangChain/LangGraph's built-in tool calling logic
- Simple graph structure with assistant and tools nodes
- Did not explicitly track which tools were used

### Simplified Approach (`research_agent_simplified.py`):
- Returns to using LangChain/LangGraph's built-in tool calling logic
- Collects evidence in a structured format
- Simpler graph structure with fewer nodes and edges

## How It Works

The simplified research agent workflow follows this pattern:

```
START → preprocessing → assistant → tools → assistant → ... → postprocessing → END
```

1. **preprocessing**: Prepares the claim for processing and initializes tracking variables
2. **assistant**: Uses the LLM with all tools available to decide which tools to use
3. **tools**: Executes the selected tools to gather evidence
4. **postprocessing**: Extracts evidence from the message history

## State Tracking

The agent tracks several pieces of state:
- `used_tools`: List of tools that have been used to gather evidence
- `evidence`: List of evidence gathered from tool calls

## Benefits of This Approach

1. **Simplicity**: Uses LangChain/LangGraph's built-in tool calling logic
2. **Efficiency**: Fewer nodes and edges in the graph
3. **Transparency**: Still tracks which tools were used
4. **Structured Output**: Collects evidence in a consistent format

## How to Test

### Using the Python Script

You can run the script directly:

```bash
python core/agents/research_agent_simplified.py
```

This will run the example tests included at the bottom of the file.

### Using pytest

You can run the tests using pytest:

```bash
pytest tests/test_research_agent_simplified.py -v
```

## Example Usage in Code

```python
from core.agents.research_agent_simplified import agent

# Test with a factual claim
factual_claim = "Albert Einstein developed the theory of relativity"
factual_result = agent.invoke({"claim": factual_claim})

# Print tools used
print("Tools Used:")
for tool_name in factual_result.get('used_tools', []):
    print(f"  {tool_name}")

# Print evidence
print("Evidence:")
for evidence in factual_result.get('evidence', []):
    print(f"  Tool: {evidence['name']}")
    print(f"  Args: {evidence['args']}")
    print(f"  Result: {evidence['result'][:100]}...")  # Show first 100 chars
    print()
```

## Requirements

Make sure you have:
1. Ollama running locally with the "mistral-nemo" model
2. All dependencies installed (`pip install -r requirements.txt`)
3. A `.env` file with any necessary environment variables
