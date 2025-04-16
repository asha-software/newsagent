"""
Run this script from /tests/langsmith/ to load env variables 
"""
import argparse
import os
import json
from langsmith import Client
from dotenv import load_dotenv

"""
Example usage:
python setup_langsmith_dataset.py --name <dataset_name> --description <dataset_description> --units <path_to_jsonl_dataset_1> <path_to_jsonl_dataset_2>
"""


def argument_parser():
    parser = argparse.ArgumentParser(description='Create a dataset')
    parser.add_argument('--name', '-n',
                        type=str, help='Name of the dataset')
    parser.add_argument('--description', '-d',
                        type=str,
                        help='Description of the dataset')
    parser.add_argument('--units', '-u',
                        nargs='+',
                        type=str,
                        help='List of paths to jsonl datasets')
    return parser.parse_args()


def create_dataset(name, description, examples):
    client = Client()
    dataset = client.create_dataset(
        dataset_name=name,
        description=description,
    )
    client.create_examples(
        dataset_id=dataset.id,
        inputs=[example['inputs'] for example in examples],
        outputs=[example['outputs'] for example in examples],
        metadata=[example['metadata'] for example in examples],
    )
    print(
        f"Dataset {name} (id={dataset.id}) created with {len(examples)} examples")


def get_examples(paths: list[str]):
    """
    paths: list of paths to json arrays of examples
    """
    examples = []
    for path in paths:
        with (open(path, 'r')) as f:
            examples.extend(json.load(f))
    return examples


def main():
    # Get the LANGCHAIN_API_KEY from the .env file
    # Make sure tests/.env variables are set
    load_dotenv("../.env", override=True)
    assert "LANGCHAIN_API_KEY" in os.environ, "Please set the LANGCHAIN_API_KEY environment variable"
    assert os.environ["LANGCHAIN_TRACING_V2"] == "true", "Please set the LANGCHAIN_TRACING_V2 environment variable to true"

    args = argument_parser()

    # Load examples from JSON, create dataset
    examples = get_examples(args.units)
    create_dataset(name=args.name, description=args.description,
                   examples=examples)


if __name__ == '__main__':
    main()
