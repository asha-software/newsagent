import pytest
import requests
import json
import os
from dotenv import load_dotenv

# Assumes you're running this from tests/ and the .env file with NEWSAGENT_API_KEY is in the root directory
load_dotenv("../.env", override=True)


@pytest.fixture
def api_endpoint():
    """Fixture for the API endpoint"""
    return "http://localhost:8001/query"


@pytest.fixture
def api_key():
    """Fixture to get API key from environment variable"""
    api_key = os.getenv("NEWSAGENT_API_KEY")
    if not api_key:
        pytest.skip("NEWSAGENT_API_KEY environment variable not set")
    return api_key


def test_api_response_structure(api_endpoint, api_key):
    """Test that API response has the expected structure"""
    # Prepare test data
    test_claim = "Philadelphia was the capital of the US. It's population today is about 1.6 million."
    payload = {"body": test_claim}

    # Make request to API
    headers = {"X-API-Key": api_key}
    response = requests.post(api_endpoint, json=payload, headers=headers)

    # Check response status
    assert (
        response.status_code == 200
    ), f"API request failed with status {response.status_code}: {response.text}"

    # Verify response is valid JSON
    try:
        result = response.json()
    except json.JSONDecodeError as e:
        pytest.fail(f"Response is not valid JSON: {str(e)}")
        print(f"Raw response content: {response}")

    for key, value in result.items():
        print(f"{key}: {str(value)[:100]}")
    # Check that required keys are present
    expected_keys = ["analyses", "final_label", "final_justification"]
    for key in expected_keys:
        assert key in result, f"Response missing '{key}' key"
    for analysis in result["analyses"]:
        assert "claim" in analysis, f"Analysis missing 'claim' key"
        assert "evidence" in analysis, f"Analysis missing 'evidence' key"
        assert "label" in analysis, f"Analysis missing 'label' key"
        assert "justification" in analysis, f"Analysis missing 'justification' key"
