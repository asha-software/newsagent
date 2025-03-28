import pytest
from core.agents.tools.tool_registry import create_tool


def test_create_tool_handles_non_json_response(monkeypatch):
    """Test that the tool returns raw text when response is not JSON"""
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


def test_create_tool_basic_get(monkeypatch):
    """Test that GET request with URL param works"""
    class MockResponse:
        def json(self):
            return {"status": "ok"}

    def mock_request(method, url, **kwargs):
        assert method == "GET"
        assert url == "https://api.com/item/42"
        return MockResponse()

    monkeypatch.setattr("requests.request", mock_request)

    tool = create_tool(
        method="GET",
        url_template="https://api.com/item/{id}",
        param_mapping={"id": "url_params"}
    )

    result = tool(id=42)
    assert result.json()["status"] == "ok"


def test_create_tool_with_default_params(monkeypatch):
    """Test default query parameters"""
    class MockResponse:
        def json(self):
            return {"result": "ok"}

    def mock_request(method, url, params, **kwargs):
        assert params == {"q": "news"}
        return MockResponse()

    monkeypatch.setattr("requests.request", mock_request)

    tool = create_tool(
        method="GET",
        url_template="https://api.com/search",
        default_params={"q": "news"}
    )

    result = tool()
    assert result.json()["result"] == "ok"


def test_create_tool_merges_headers(monkeypatch):
    """Ensure headers passed during call override defaults"""
    class MockResponse:
        def json(self):
            return {"ok": True}

    def mock_request(method, url, headers, **kwargs):
        assert headers["X-Test"] == "override"
        return MockResponse()

    monkeypatch.setattr("requests.request", mock_request)

    tool = create_tool(
        method="GET",
        url_template="https://api.com/test",
        headers={"X-Test": "default"}
    )

    result = tool(headers={"X-Test": "override"})
    assert result.json()["ok"] is True


def test_create_tool_with_target_fields(monkeypatch):
    """Extract nested fields from JSON using target_fields"""
    class MockResponse:
        def json(self):
            return {"data": {"name": "John"}}

    def mock_request(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr("requests.request", mock_request)

    tool = create_tool(
        method="GET",
        url_template="https://api.com/user",
        target_fields=[["data", "name"]]
    )

    result = tool()
    assert result == ["John"]


def test_create_tool_with_multiple_target_fields(monkeypatch):
    """Test multiple nested paths in JSON"""
    class MockResponse:
        def json(self):
            return {"a": {"b": 1}, "x": {"y": 2}}

    def mock_request(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr("requests.request", mock_request)

    tool = create_tool(
        method="GET",
        url_template="https://api.com/complex",
        target_fields=[["a", "b"], ["x", "y"]]
    )

    result = tool()
    assert result == [1, 2]


def test_create_tool_with_post_and_json_payload(monkeypatch):
    """Check POST request with JSON body"""
    class MockResponse:
        def json(self):
            return {"msg": "created"}

    def mock_request(method, url, json=None, **kwargs):
        assert method == "POST"
        assert json == {"name": "test"}
        return MockResponse()

    monkeypatch.setattr("requests.request", mock_request)

    tool = create_tool(
        method="POST",
        url_template="https://api.com/create"
    )

    result = tool(json={"name": "test"})
    assert result.json()["msg"] == "created"


def test_create_tool_custom_signature(monkeypatch):
    """Test tool with dynamic signature and argument mapping"""
    class MockResponse:
        def json(self):
            return {"ok": True}

    def mock_request(method, url, params=None, **kwargs):
        assert params == {"query": "climate"}
        return MockResponse()

    monkeypatch.setattr("requests.request", mock_request)

    tool = create_tool(
        method="GET",
        url_template="https://api.com/query",
        param_mapping={"query": "params"}
    )

    result = tool(query="climate")
    assert result.json()["ok"]


def test_create_tool_returns_full_response(monkeypatch):
    """Test when no target_fields: return full response object"""
    class MockResponse:
        def __init__(self):
            self.status_code = 200

        def json(self):
            return {"status": "ok"}

    def mock_request(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr("requests.request", mock_request)

    tool = create_tool(
        method="GET",
        url_template="https://api.com/full"
    )

    response = tool()
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_tool_with_indexed_path(monkeypatch):
    """Extract value using list index in path"""
    class MockResponse:
        def json(self):
            return {"items": ["apple", "banana"]}

    def mock_request(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr("requests.request", mock_request)

    tool = create_tool(
        method="GET",
        url_template="https://api.com/list",
        target_fields=[["items", 1]]
    )

    result = tool()
    assert result == ["banana"]
