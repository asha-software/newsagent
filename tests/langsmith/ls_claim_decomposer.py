from langsmith import Client
from langchain_ollama import ChatOllama

ls_client = Client()
from test_data.claim_decomposer_test_data import basic_test_cases

dataset = client.create_dataset(
    name="claim_decomposer_test_dataset",
    description="Test dataset for the claim decomposer agent",
    tags=["claim_decomposer"],
)

client.create_examples(
    dataset_id=dataset.id,
    examples=basic_test_cases,
)

# Evaluation functions for the claim decomposer
def number_of_claims_diff(outputs: dict, reference_outputs: dict) -> int:
    """Check if the number of claims in the output matches the expected number."""
    predicted_claims = outputs["claims"]
    reference_claims = reference_outputs["claims"]
    return len(predicted_claims) - len(reference_claims)

def claims_match(outputs: dict, reference_outputs: dict) -> bool:
    """Check if the claims in the output match the expected claims."""
    LLM_OUTPUT_FORMAT = {
        "type": "object",
        "properties": {
            "label": {
                "type": "boolean",
                "description": "true if the statement lists match, false otherwise"
            },
            "explanation": {
                "type": "string",
                "description": "explanation of the label chosen"
            }
        },
        "required": ["label", "explanation"]
    }
    # Initialize the LLM with the specified output format
    llm = ChatOllama(
        model="deepseek-r1:32b", 
        temperature=0,
        format=LLM_OUTPUT_FORMAT)
        
    with open("prompts/claim_decomposer_system_prompt.txt", "r") as f:
        prompt_template = f.read()
    
    reference_claims = reference_outputs["claims"]
    predicted_claims = outputs["claims"]
    prompt = prompt_template.format(reference_claims=reference_claims, predicted_claims=predicted_claims)
    response = llm.invoke(prompt)


