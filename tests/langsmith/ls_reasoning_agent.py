"""
From tests/langsmith
python ls_reasoning_agent.py -p <prefix name>
"""

import argparse
import json
import os
import sys
from dotenv import load_dotenv
from langsmith import Client
from pathlib import Path
from langchain_ollama import ChatOllama
from dotenv import load_dotenv

#Load required API keys and endpoint
load_dotenv(".env", override=True)

# rooth path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def argument_parser():
    parser = argparse.ArgumentParser(description='Evaluate the reasoning agent')
    parser.add_argument('--experiment_prefix', '-p',
                        type=str, help='Prefix for the experiment name')
    return parser.parse_args()


def load_prompt(path):
    with open(path, "r") as f:
        return f.read()


def target_function(inputs) -> dict:
    from core.agents.reasoning_agent import reasoning_agent
    result = reasoning_agent.invoke(inputs)
    return {
        "output": {
            "label": result["label"],
            "justification": result["justification"]
        }
    }



def label_match(outputs: dict, reference_outputs: dict) -> dict:
    """Check if the predicted label matches the reference label."""
    predicted = outputs["output"]["label"]
    reference = reference_outputs["label"]
    return {
        "key": "label_match",
        "score": predicted == reference,
        "comment": f"Expected '{reference}', got '{predicted}'"
    }


def justification_coherence(outputs: dict, reference_outputs: dict) -> dict:
    """Check if the justification logically supports the predicted label (using LLM evaluation)."""
    predicted_label = outputs["output"]["label"]
    justification = outputs["output"]["justification"]

    prompt_template = load_prompt("prompts/reasoning_coherence_prompt.txt")
    prompt = prompt_template.format(
        predicted_label=predicted_label,
        justification=justification
    )


    llm_eval = ChatOllama(
        model="llama3",
        temperature=0,
        format={
            "type": "object",
            "properties": {
                "coherent": {"type": "boolean"},
                "reason": {"type": "string"}
            },
            "required": ["coherent", "reason"]
        }
    )

    response = llm_eval.invoke(prompt).content
    eval_result = json.loads(response)

    return {
        "key": "justification_coherence",
        "score": eval_result["coherent"],
        "comment": eval_result["reason"]
    }


def main():
    load_dotenv("../.env", override=True)
    assert "LANGCHAIN_API_KEY" in os.environ, "Please set LANGCHAIN_API_KEY environment variable"
    assert os.environ["LANGCHAIN_TRACING_V2"] == "true", "Please set LANGCHAIN_TRACING_V2 environment variable to true"

    args = argument_parser()
    ls_client = Client()
    experiment_results = ls_client.evaluate(
        target_function,
        data="my_dataset11",
        evaluators=[label_match, justification_coherence],
        experiment_prefix=args.experiment_prefix
    )


if __name__ == "__main__":
    main()
