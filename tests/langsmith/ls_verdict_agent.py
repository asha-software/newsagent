"""
From tests/langsmith
Run with:
python ls_verdict_agent.py -p <prefix name>
"""

import argparse
import json
import os
import sys
from dotenv import load_dotenv
from langsmith import Client
from pathlib import Path
from langchain_ollama import ChatOllama

# Load environment variables
load_dotenv(".env", override=True)

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def argument_parser():
    parser = argparse.ArgumentParser(description='Evaluate the verdict agent')
    parser.add_argument('--experiment_prefix', '-p',
                        type=str, help='Prefix for the experiment name')
    return parser.parse_args()


def load_prompt(path):
    with open(path, "r") as f:
        return f.read()


def target_function(inputs) -> dict:
    from core.agents.verdict_agent import verdict_agent
    result = verdict_agent.invoke(inputs)
    return {
        "output": {
            "final_label": result["final_label"],
            "final_justification": result["final_justification"]
        }
    }


def label_match(outputs: dict, reference_outputs: dict) -> dict:
    predicted = outputs["output"]["final_label"]
    expected = reference_outputs["final_label"]
    return {
        "key": "label_match",
        "score": predicted == expected,
        "comment": f"Expected '{expected}', got '{predicted}'"
    }


def justification_coherence(outputs: dict, reference_outputs: dict, example) -> dict:
    predicted_label = outputs["output"]["final_label"]
    justification = outputs["output"]["final_justification"]

    try:
        claim_labels = example.inputs.get("labels")

        prompt_template = load_prompt("prompts/verdict_coherence_prompt.txt")
        prompt = prompt_template.format(
            predicted_label=predicted_label,
            claim_labels=claim_labels,
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

    except Exception as e:
        return {
            "key": "justification_coherence",
            "score": False,
            "comment": f"Error during evaluation: {e}"
        }


def main():
    load_dotenv("../.env", override=True)
    assert "LANGCHAIN_API_KEY" in os.environ, "Please set LANGCHAIN_API_KEY environment variable"
    assert os.environ["LANGCHAIN_TRACING_V2"] == "true", "Please set LANGCHAIN_TRACING_V2=true"

    args = argument_parser()
    ls_client = Client()
    ls_client.evaluate(
        target_function,
        data="test",
        evaluators=[label_match, justification_coherence],
        experiment_prefix=args.experiment_prefix
    )


if __name__ == "__main__":
    main()
