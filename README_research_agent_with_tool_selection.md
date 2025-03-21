# Research Agent with Tool Selection

This version of the tool enhances the original research agent by adding a tool selection phase before evidence gathering. The agent now follows a two-step process:

1. First, it analyzes the claim and determines which tools would be most appropriate to use
2. Then, it uses only the selected tools to gather evidence about the claim

## Files Added

- `core/agents/prompts/tool_selection_prompt.txt`: System prompt for the tool selection phase
- `core/agents/research_agent_with_tool_selection.py`: Enhanced research agent implementation
- `tests/test_research_agent_with_tool_selection.py`: Test suite for the enhanced agent
- `core/agents/nb_research_agent_with_tool_selection.ipynb`: Jupyter notebook demonstrating the enhanced agent

## How It Works

The enhanced research agent workflow includes a new "tool selection" node in the LangGraph:

```
START → preprocessing → tool_selection → assistant → tools → postprocessing → END
```

1. **preprocessing**: Prepares the claim for processing
2. **tool_selection**: Analyzes the claim and determines which tools would be appropriate (NEW)
3. **assistant**: Uses an LLM with only the selected tools to analyze the claim
4. **tools**: Executes tool calls to gather evidence
5. **postprocessing**: Extracts evidence from tool responses

## Tool Selection Format

The tool selection phase outputs a structured JSON object with decisions and reasoning for each tool:

```json
{
  "tool_selections": {
    "wikipedia": {
      "selected": true,
      "reasoning": "This tool is useful for retrieving factual information about Einstein and the theory of relativity."
    },
    "multiply": {
      "selected": false,
      "reasoning": "This claim does not involve multiplication operations."
    },
    "add": {
      "selected": false,
      "reasoning": "This claim does not involve addition operations."
    },
    "divide": {
      "selected": false,
      "reasoning": "This claim does not involve division operations."
    }
  }
}
```

## How to Test

### Using the Test Suite

```bash
# Run all tests for the enhanced research agent
pytest tests/test_research_agent_with_tool_selection.py

# Run a specific test
pytest tests/test_research_agent_with_tool_selection.py::test_tool_selection
```

### Using the Python Script

You can run the script directly:

```bash
python core/agents/research_agent_with_tool_selection.py
```

This will run the example tests included at the bottom of the file.

### Using the Jupyter Notebook

```bash
# Navigate to the core/agents directory
cd core/agents

# Start Jupyter notebook
jupyter notebook
```

Then open `nb_research_agent_with_tool_selection.ipynb` and run the cells to see the agent in action.

## Example Usage in Code

```python
from core.agents.research_agent_with_tool_selection import agent

# Test with a factual claim
factual_claim = "Albert Einstein developed the theory of relativity"
factual_result = agent.invoke({"claim": factual_claim})

# Print tool selections
print("Tool Selections:")
for tool_name, selection in factual_result.get('tool_selections', {}).items():
    selected = selection.get('selected', False)
    reasoning = selection.get('reasoning', 'No reasoning provided')
    print(f"  {tool_name}: {selected} - {reasoning}")

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
