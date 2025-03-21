from pprint import pprint
import json
from IPython.display import Image, display
from dotenv import load_dotenv
import importlib
import os
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing import Annotated, TypedDict


MODEL = "mistral-nemo"
TEMPERATURE = 0
# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
# Try to load .env file from project root
load_dotenv(os.path.join(os.path.dirname(script_dir), '.env'), override=True)
PATH_TO_FILE = os.path.abspath(__file__)


TOOL_REGISTRY = {
    'core.agents.tools.calculator': ['multiply', 'add', 'divide'],
    'core.agents.tools.wikipedia': ['wikipedia']
}


def import_function(module_name, function_name):
    """Dynamically imports a function from a module.

    Args:
        module_name: The name of the module (e.g., "my_module").
        function_name: The name of the function to import (e.g., "my_function").

    Returns:
        The imported function, or None if the module or function is not found.
    """
    try:
        module = importlib.import_module(module_name)
        function = getattr(module, function_name)
        return function
    except (ImportError, AttributeError) as e:
        print(f"I'm in cwd: {os.getcwd()}")
        print(f"Available modules: {os.listdir(os.getcwd())}")
        print(
            f"Error: Could not import function '{function_name}' from module '{module_name}'.")
        print(f"Exception: {e}")
        return None


tools = [import_function(module, function) for module,
         functions in TOOL_REGISTRY.items() for function in functions]
print(f"Tools: {[tool.__name__ for tool in tools]}")


llm = ChatOllama(
    model=MODEL,
    temperature=TEMPERATURE,
    # base_url="http://host.docker.internal:11434", # if running in the studio
).bind_tools(tools)


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    claim: str
    # New field to track tool selections
    tool_selections: dict
    # {'name': tool name, 'args': {kwargs}, 'result': str}
    evidence: list[dict]


# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(script_dir, 'prompts/research_agent_system_prompt.txt'), 'r') as f:
    sys_msg = SystemMessage(content=f.read())

with open(os.path.join(script_dir, 'prompts/tool_selection_prompt.txt'), 'r') as f:
    tool_selection_msg = SystemMessage(content=f.read())


def preprocessing(state: State):
    """
    Preprocesses state before sending to the assistant for tool routing.
    Currently, this just extracts the claim from the state and sets it as a HumanMessage
    following the SystemMessage
    """
    state['messages'] = [sys_msg, HumanMessage(content=state['claim'])]
    return state


def tool_selection(state: State) -> State:
    """
    Analyzes the claim and determines which tools would be appropriate to use.
    Returns a dictionary with tool names as keys and boolean values indicating
    whether each tool should be used.
    """
    # Create a message with the tool selection prompt and the claim
    messages = [tool_selection_msg, HumanMessage(content=state['claim'])]
    
    # Get the LLM's response
    response = llm.invoke(messages)
    
    # Extract the tool selections from the response
    try:
        # Try to parse the JSON directly from the response content
        selections_data = json.loads(response.content)
        tool_selections = selections_data.get('tool_selections', {})
    except json.JSONDecodeError:
        # If direct parsing fails, try to extract JSON from the text
        content = response.content
        start_idx = content.find('{')
        end_idx = content.rfind('}') + 1
        if start_idx >= 0 and end_idx > start_idx:
            json_str = content[start_idx:end_idx]
            try:
                selections_data = json.loads(json_str)
                tool_selections = selections_data.get('tool_selections', {})
            except json.JSONDecodeError:
                # If all parsing attempts fail, use default selections (all True)
                print("Failed to parse tool selections, using defaults")
                tool_selections = {
                    tool.__name__: {"selected": True, "reasoning": "Default selection"} 
                    for tool in tools
                }
        else:
            # If no JSON-like structure is found, use default selections
            tool_selections = {
                tool.__name__: {"selected": True, "reasoning": "Default selection"} 
                for tool in tools
            }
    
    # Print the tool selections for debugging
    print("Tool Selections:")
    for tool_name, selection in tool_selections.items():
        selected = selection.get('selected', False)
        reasoning = selection.get('reasoning', 'No reasoning provided')
        print(f"  {tool_name}: {selected} - {reasoning}")
    
    return {"tool_selections": tool_selections}


def assistant(state: State) -> State:
    """
    Uses the LLM to generate a response based on the claim and selected tools.
    """
    # Filter the tools based on the tool selections
    selected_tools = []
    for tool in tools:
        tool_name = tool.__name__
        selection = state['tool_selections'].get(tool_name, {})
        if selection.get('selected', False):
            selected_tools.append(tool)
    
    # If no tools were selected, use all tools as a fallback
    if not selected_tools:
        selected_tools = tools
        print("No tools were selected, using all tools as fallback")
        # Update tool_selections to mark all tools as selected
        for tool in tools:
            tool_name = tool.__name__
            state['tool_selections'][tool_name] = {
                "selected": True,
                "reasoning": "Selected as fallback because no tools were explicitly selected"
            }
    else:
        print(f"Using selected tools: {[tool.__name__ for tool in selected_tools]}")
    
    # Bind only the selected tools to the LLM
    llm_with_selected_tools = llm.bind_tools(selected_tools)
    
    # Generate a response using the selected tools
    response = llm_with_selected_tools.invoke(state['messages'])
    
    return {"messages": response}


def postprocessing(state: State) -> State:
    """
    Scan the message history to extract tool calls and results into tuples:
    (tool_name, tool_args, tool_result) for the 'evidence' list in the state
    """
    evidence = []
    for i in range(len(state['messages'])):
        message = state['messages'][i]
        if isinstance(message, AIMessage) and hasattr(message, 'tool_calls'):
            for tool_call in message.tool_calls:
                # Scan later messages for the corresponding ToolMessage
                for j in range(i + 1, len(state['messages'])):
                    next_message = state['messages'][j]
                    if isinstance(next_message, ToolMessage) and next_message.tool_call_id == tool_call['id']:
                        # Found the corresponding ToolMessage
                        evidence.append({
                            'name': tool_call['name'],
                            'args': tool_call['args'],
                            'result': next_message.content})
                        break

    return {'evidence': evidence}


# Graph
builder = StateGraph(State)

# Define nodes: these do the work
builder.add_node("preprocessing", preprocessing)
builder.add_node("tool_selection", tool_selection)
builder.add_node("assistant", assistant)
builder.add_node("tools", ToolNode(tools))
builder.add_node("postprocessing", postprocessing)

# Define edges: these determine how the control flow moves
builder.add_edge(START, "preprocessing")
builder.add_edge("preprocessing", "tool_selection")
builder.add_edge("tool_selection", "assistant")
builder.add_conditional_edges(
    source="assistant",
    path=tools_condition,
    path_map={'tools': 'tools', '__end__': 'postprocessing'}
)
builder.add_edge("tools", "assistant")
builder.add_edge("postprocessing", END)

agent = builder.compile()

# Example usage
if __name__ == "__main__":
    # Test with a factual claim
    factual_claim = "Albert Einstein developed the theory of relativity"
    factual_result = agent.invoke({"claim": factual_claim})
    
    print("\nFactual Claim Test:")
    print(f"Claim: {factual_claim}")
    print("Tool Selections:")
    for tool_name, selection in factual_result.get('tool_selections', {}).items():
        selected = selection.get('selected', False)
        reasoning = selection.get('reasoning', 'No reasoning provided')
        print(f"  {tool_name}: {selected} - {reasoning}")
    
    print("Evidence:")
    for evidence in factual_result.get('evidence', []):
        print(f"  Tool: {evidence['name']}")
        print(f"  Args: {evidence['args']}")
        print(f"  Result: {evidence['result'][:100]}..." if len(evidence['result']) > 100 else f"  Result: {evidence['result']}")
        print()
    
    # Test with a mathematical claim
    math_claim = "12 multiplied by 10 equals 120"
    math_result = agent.invoke({"claim": math_claim})
    
    print("\nMathematical Claim Test:")
    print(f"Claim: {math_claim}")
    print("Tool Selections:")
    for tool_name, selection in math_result.get('tool_selections', {}).items():
        selected = selection.get('selected', False)
        reasoning = selection.get('reasoning', 'No reasoning provided')
        print(f"  {tool_name}: {selected} - {reasoning}")
    
    print("Evidence:")
    for evidence in math_result.get('evidence', []):
        print(f"  Tool: {evidence['name']}")
        print(f"  Args: {evidence['args']}")
        print(f"  Result: {evidence['result']}")
        print()
