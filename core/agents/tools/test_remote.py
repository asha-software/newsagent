from core.agents.tools.remote_tool import (
    create_remote_tool,
    get_available_methods,
    get_method_info,
)

MOCK_METHODS = {
    "get_article": {
        "description": "Get information about a news article",
        "input_types": [str],  # URL
        "mock_response": {
            "title": "News Article",
            "author": "John Doe",
            "published_date": "2025-03-22",
            "content": "This is an example news article content.",
        },
    }
}


def test_function_based_approach():
    """Test the function-based approach"""
    print("\nTesting Function-Based Approach")

    # Create a tool instance using the function-based approach
    tool_instance = create_remote_tool(
        name="NewsAPI",
        url="https://example.com/api",
        api_key="test_key",
        mock=True,
        mock_methods=MOCK_METHODS,
    )

    # Get available methods
    methods = get_available_methods()
    print(f"Available methods: {methods}")

    # Get method info
    method_info = get_method_info("get_article")
    print(f"Method info: {method_info}")

    # Use the tool
    result = tool_instance.use_tool(
        "get_article", ["https://example.com/sample-article"]
    )
    print(f"Method result: {result}")


if __name__ == "__main__":
    test_function_based_approach()
