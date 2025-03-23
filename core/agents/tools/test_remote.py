from remote_tool import RemoteTool

MOCK_METHODS = {
    "get_article": {
        "description": "Get information about a news article",
        "input_types": [str],  # URL
        "mock_response": {
            "title": "News Article",
            "author": "John Doe",
            "published_date": "2025-03-22",
            "content": "This is an example news article content."
        }
    }
}

def test_mock_mode():
    """Test RemoteTool in mock mode"""
    print("\nTesting Mock Mode")
    
    tool = RemoteTool(
        name="NewsAPI",
        url="https://example.com/api",
        api_key="test_key",
        mock=True,
        mock_methods=MOCK_METHODS
    )

    methods = tool.get_available_methods()
    print(f"Available methods: {methods}")

    result = tool.use_tool("get_article", ["https://example.com/sample-article"])
    print(f"Method result: {result}")

if __name__ == "__main__":
    test_mock_mode()
