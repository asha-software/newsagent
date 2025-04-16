import argparse
from dotenv import load_dotenv
from langsmith import Client
import os
from pathlib import Path
import sys
from core.agents.utils.common_types import Evidence

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def argument_parser():
    parser = argparse.ArgumentParser(
        description='Evaluate the claim decomposer')
    parser.add_argument('--experiment_prefix', '-p',
                        type=str, help='Prefix for the experiment name')
    return parser.parse_args()


def target_function(initial_state):

    # Get the model name from the environment variable
    load_dotenv(project_root / "core" / ".env", override=True)
    assert "RESEARCH_AGENT_MODEL" in os.environ, "Please set the RESEARCH_AGENT_MODEL environment variable"
    model = os.environ["RESEARCH_AGENT_MODEL"]

    # Instantiate the research agent
    from core.agents.research_agent import create_agent
    agent = create_agent(model=model,
                         builtin_tools=['calculator', 'wikipedia',
                                        'web_search', 'wolframalpha']
                         )
    results = agent.invoke(initial_state)
    return results['evidence']


def evaluate_tool_choices(outputs: list[Evidence], reference_outputs: list[Evidence]) -> bool:
    # need to check that the correct tool was invoked
    ref_toolset = set([ref['name'] for ref in reference_outputs['evidence']])
    output_toolset = set([tool_call['name']
                         for tool_call in outputs['output']])

    # Check that the tools invoked are the same
    if ref_toolset != output_toolset:
        print(
            f"Tool mismatch: expected tool calls on {ref_toolset}, got tool calls on {output_toolset}")
        return False
    return True


def main():
    # Make sure tests/.env variables are set
    load_dotenv("../.env", override=True)
    assert "LANGCHAIN_API_KEY" in os.environ, "Please set the LANGCHAIN_API_KEY environment variable"
    assert os.environ["LANGCHAIN_TRACING_V2"] == "true", "Please set the LANGCHAIN_TRACING_V2 environment variable to true"

    args = argument_parser()
    ls_client = Client()
    experiment_results = ls_client.evaluate(
        target_function,
        data="research_agent_tool_usage",
        evaluators=[evaluate_tool_choices],
        experiment_prefix=args.experiment_prefix
    )


if __name__ == "__main__":
    main()
