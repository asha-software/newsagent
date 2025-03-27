def test_create_tool_handles_non_json_response(monkeypatch):
    from core.agents.tools.tool_registry import create_tool

    class MockResponse:
        def __init__(self):
            self.text = "Plain text response"

        def json(self):
            raise ValueError("Not a JSON")

    def mock_request(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr("requests.request", mock_request)

    my_tool = create_tool(
        method="GET",
        url_template="https://example.com/data",
        docstring="Test tool that may return non-JSON."
    )

    result = my_tool()
    assert result == "Plain text response"
