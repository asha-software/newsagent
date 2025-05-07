"""
From tests/langsmith
python ls_claim_decomposer.py -p <prefix name>
"""

import argparse
from dotenv import load_dotenv
from langsmith import Client
import os
from pathlib import Path
import sys


# Add project root to sys path so we can import from core.agents
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def argument_parser():
    parser = argparse.ArgumentParser(
        description='Evaluate the claim decomposer')
    parser.add_argument('--experiment_prefix', '-p',
                        type=str, help='Prefix for the experiment name')
    return parser.parse_args()


def target_function(initial_state) -> list[str]:
    from core.agents.claim_decomposer import claim_decomposer
    result = claim_decomposer.invoke(initial_state)
    return result["claims"]


def number_of_claims_diff(outputs: dict, reference_outputs: dict) -> int:
    """Check if the number of claims in the output matches the expected number."""
    predicted_claims = outputs["output"]
    reference_claims = reference_outputs["claims"]
    return len(predicted_claims) - len(reference_claims)


def main():
    # Make sure tests/.env variables are set
    load_dotenv("../.env", override=True)
    assert "LANGCHAIN_API_KEY" in os.environ, "Please set the LANGCHAIN_API_KEY environment variable"
    assert os.environ["LANGCHAIN_TRACING_V2"] == "true", "Please set the LANGCHAIN_TRACING_V2 environment variable to true"

    args = argument_parser()
    ls_client = Client()
    experiment_results = ls_client.evaluate(
        target_function,
        data="claim_decomp_multiple",
        evaluators=[number_of_claims_diff],
        experiment_prefix=args.experiment_prefix
    )


if __name__ == "__main__":
    main()
