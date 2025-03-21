
from dotenv import load_dotenv
import json
import os
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing import Annotated, TypedDict


MODEL = "mistral-nemo"
TEMPERATURE = 0
load_dotenv('.env', override=True)

"""
Define State, LLM output schema, and LLM
"""


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    text: str
    claims: list[str]


LLM_OUTPUT_FORMAT = {
    "type": "array",
    "items": {
        "type": "string"
    }
}

llm = ChatOllama(
    model=MODEL,
    temperature=TEMPERATURE,
    format=LLM_OUTPUT_FORMAT
)

"""
Build the graph
"""

with open("prompts/claim_decomposer_system_prompt.txt", "r") as f:
    system_prompt = f.read()
system_message = SystemMessage(content=system_prompt)


def preprocessing(state: State) -> State:
    """
    Preprocesses state before sending to the assistant for decomposition.
    Currently, this just extracts the text from the state, and sets it
    as a HumanMessage following the SystemMessage
    """
    state['messages'] = [system_message, HumanMessage(content=state['text'])]
    return state


def assistant(state: State) -> State:
    """
    Gets the LLM response to System and Human prompt
    """
    response = llm.invoke(state['messages'])
    return {'messages': response}


def postprocessing(state: State) -> State:
    """
    Postprocesses the LLM response to extract the claims
    Using format output on the LLM, we expect the AIMessage.content to be parsable
    as a list of strings
    """
    # We assume the last message in the state is the AI response
    message = state['messages'][-1]
    assert isinstance(
        message, AIMessage), "Postprocessing node expected the last message to be an AIMessage"
    try:
        claims = json.loads(message.content)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from claim decomposer: {e}")

    return {'claims': claims}


builder = StateGraph(State)

# Define nodes
builder.add_node("preprocessing", preprocessing)
builder.add_node("assistant", assistant)
builder.add_node("postprocessing", postprocessing)

# Define edges
builder.add_edge(START, "preprocessing")
builder.add_edge("preprocessing", "assistant")
builder.add_edge("assistant", "postprocessing")
builder.add_edge("postprocessing", END)

claim_decomposer = builder.compile()

if __name__ == "__main__":
    text_space = """
    The Apollo 11 mission landed humans on the Moon for the first time on July 20, 1969. 
    Neil Armstrong was the first person to walk on the lunar surface.
    The mission was launched by NASA using a Saturn V rocket.
    """
    
    text_historical = """
    The Treaty of Versailles was signed on June 28, 1919, formally ending World War I. 
    Germany was forced to accept responsibility for the war and pay reparations.
    The treaty redrew national boundaries in Europe, creating new countries like Poland and Czechoslovakia.
    President Woodrow Wilson represented the United States at the Paris Peace Conference.
    """
    
    text_scientific = """
    The Human Genome Project was completed in April 2003, two years ahead of schedule.
    Scientists successfully mapped all 3 billion base pairs in human DNA.
    The project cost approximately $3 billion and involved researchers from 20 institutions across 6 countries.
    This breakthrough has led to advances in understanding genetic diseases and developing personalized medicine.
    """
    
    text_entertainment = """
    The first Academy Awards ceremony was held on May 16, 1929, at the Hollywood Roosevelt Hotel.
    Only 270 people attended the first ceremony, and tickets cost $5 each.
    The ceremony lasted only 15 minutes, and the awards were announced three months earlier.
    "Wings" won the first Academy Award for Best Picture, while Emil Jannings and Janet Gaynor won the first acting awards.
    """
    
    print("\nExample 1: Space Exploration")
    result_space = claim_decomposer.invoke({'text': text_space})
    for claim in result_space['claims']:
        print(f"- {claim}")
    
    print("\nExample 2: Historical/Political")
    result_historical = claim_decomposer.invoke({'text': text_historical})
    for claim in result_historical['claims']:
        print(f"- {claim}")
    
    print("\nExample 3: Scientific/Technological")
    result_scientific = claim_decomposer.invoke({'text': text_scientific})
    for claim in result_scientific['claims']:
        print(f"- {claim}")
    
    print("\nExample 4: Sports/Entertainment")
    result_entertainment = claim_decomposer.invoke({'text': text_entertainment})
    for claim in result_entertainment['claims']:
        print(f"- {claim}")
