"""
From tests/langsmith
python ls_claim_decomposer.py -p <prefix name>
"""

import argparse
from langsmith import Client
from pathlib import Path
import sys


# Add project root to sys path so we can import from core.agents
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# fmt: off
# 

# fmt: on


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
    args = argument_parser()
    ls_client = Client()
    experiment_results = ls_client.evaluate(
        target_function,
        data="claim_decomposer_all_examples",
        evaluators=[number_of_claims_diff],
        experiment_prefix=args.experiment_prefix
    )


if __name__ == "__main__":
    main()
