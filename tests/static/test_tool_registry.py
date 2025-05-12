from typing import Dict, Any
import json

import pytest
from core.agents.tools.tool_registry import create_tool, extract_fields


def test_create_tool_handles_non_json_response(monkeypatch):
    class MockResponse:
        def __init__(self):
            self.text = "Plain text response"

        def json(self):
            raise ValueError("Not a JSON")

    def mock_request(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr("requests.request", mock_request)

    my_tool = create_tool(
        name="non_json_tool",
        method="GET",
        url_template="https://example.com/data",
        docstring="Test tool that may return non-JSON.",
        param_mapping={},
    )

    result_str = my_tool.invoke({})
    result_list = json.loads(result_str)
    assert result_list[0]["content"] == "Plain text response"


def test_create_tool_basic_get(monkeypatch):
    class MockResponse:
        def json(self):
            return {"status": "ok"}

    def mock_request(method, url, **kwargs):
        assert method == "GET"
        assert url == "https://api.com/item/42"
        return MockResponse()

    monkeypatch.setattr("requests.request", mock_request)

    tool = create_tool(
        name="basic_get_tool",
        method="GET",
        url_template="https://api.com/item/{id}",
        param_mapping={"id": {"type": "int", "for": "url_params"}},
    )

    result_str = tool.invoke({"id": 42})
    result_list = json.loads(result_str)
    assert result_list[0]["content"]["status"] == "ok"


def test_create_tool_with_default_params(monkeypatch):
    class MockResponse:
        def json(self):
            return {"result": "ok"}

    def mock_request(method, url, params, **kwargs):
        assert params == {"q": "news"}
        return MockResponse()

    monkeypatch.setattr("requests.request", mock_request)

    tool = create_tool(
        name="default_params_tool",
        method="GET",
        url_template="https://api.com/search",
        default_params={"q": "news"},
        param_mapping={},
    )

    result_str = tool.invoke({})
    result_list = json.loads(result_str)
    assert result_list[0]["content"]["result"] == "ok"


def test_create_tool_merges_headers(monkeypatch):
    class MockResponse:
        def json(self):
            return {"ok": True}

    def mock_request(method, url, headers, **kwargs):
        assert headers["x_test"] == "override"
        return MockResponse()

    monkeypatch.setattr("requests.request", mock_request)

    tool = create_tool(
        name="merge_headers_tool",
        method="GET",
        url_template="https://api.com/test",
        headers={"x_test": "default"},
        param_mapping={"x_test": {"type": "str", "for": "headers"}},
    )

    result_str = tool.invoke({"x_test": "override"})
    result_list = json.loads(result_str)
    assert result_list[0]["content"]["ok"] is True


def test_create_tool_with_target_fields(monkeypatch):
    class MockResponse:
        def json(self):
            return {"data": {"name": "John"}}

    def mock_request(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr("requests.request", mock_request)

    tool = create_tool(
        name="target_fields_tool",
        method="GET",
        url_template="https://api.com/user",
        target_fields=[["data", "name"]],
        param_mapping={},
    )

    result_str = tool.invoke({})
    result_list = json.loads(result_str)
    assert result_list[0]["content"] == ["John"]


def test_create_tool_with_multiple_target_fields(monkeypatch):
    class MockResponse:
        def json(self):
            return {"a": {"b": 1}, "x": {"y": 2}}

    def mock_request(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr("requests.request", mock_request)

    tool = create_tool(
        name="multiple_target_fields_tool",
        method="GET",
        url_template="https://api.com/complex",
        target_fields=[["a", "b"], ["x", "y"]],
        param_mapping={},
    )

    result_str = tool.invoke({})
    result_list = json.loads(result_str)
    assert result_list[0]["content"] == [1, 2]


def test_create_tool_with_post_and_json_payload(monkeypatch):
    class MockResponse:
        def json(self):
            return {"msg": "created"}

    def mock_request(method, url, json=None, **kwargs):
        assert method == "POST"
        assert json == {"name": "test"}
        return MockResponse()

    monkeypatch.setattr("requests.request", mock_request)

    tool = create_tool(
        name="post_json_tool",
        method="POST",
        url_template="https://api.com/create",
        param_mapping={"name": {"type": "str", "for": "json"}},
    )

    result_str = tool.invoke({"name": "test"})
    result_list = json.loads(result_str)
    assert result_list[0]["content"]["msg"] == "created"


def test_create_tool_custom_signature(monkeypatch):
    class MockResponse:
        def json(self):
            return {"ok": True}

    def mock_request(method, url, params=None, **kwargs):
        assert params == {"query": "climate"}
        return MockResponse()

    monkeypatch.setattr("requests.request", mock_request)

    tool = create_tool(
        name="custom_signature_tool",
        method="GET",
        url_template="https://api.com/query",
        param_mapping={"query": {"type": "str", "for": "params"}},
    )

    result_str = tool.invoke({"query": "climate"})
    result_list = json.loads(result_str)
    assert result_list[0]["content"]["ok"]


def test_create_tool_returns_full_response(monkeypatch):
    class MockResponse:
        def __init__(self):
            self.status_code = 200

        def json(self):
            return {"status": "ok"}

    def mock_request(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr("requests.request", mock_request)

    tool = create_tool(
        name="full_response_tool",
        method="GET",
        url_template="https://api.com/full",
        param_mapping={},
    )

    result_str = tool.invoke({})
    result_list = json.loads(result_str)
    assert result_list[0]["content"]["status"] == "ok"


def test_create_tool_with_query_and_headers(monkeypatch):
    class MockResponse:
        def json(self):
            return {"results": [1, 2, 3]}


def test_create_tool_with_json_and_data_conflict(monkeypatch):
    class MockResponse:
        def json(self):
            return {"ok": True}

    def mock_request(method, url, json=None, data=None, **kwargs):
        assert json == {"username": "alice"}
        assert data == {}
        return MockResponse()

    monkeypatch.setattr("requests.request", mock_request)

    tool = create_tool(
        name="json_vs_data_tool",
        method="POST",
        url_template="https://api.com/register",
        param_mapping={"username": {"type": "str", "for": "json"}},
    )

    result_str = tool.invoke({"username": "alice"})
    result_list = json.loads(result_str)
    assert result_list[0]["content"]["ok"]


def test_create_tool_with_nested_json_path(monkeypatch):
    class MockResponse:
        def json(self):
            return {"outer": {"middle": {"inner": 42}}}

    def mock_request(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr("requests.request", mock_request)

    tool = create_tool(
        name="nested_json_tool",
        method="GET",
        url_template="https://api.com/data",
        target_fields=[["outer", "middle", "inner"]],
        param_mapping={},
    )

    result_str = tool.invoke({})
    result_list = json.loads(result_str)
    assert result_list[0]["content"] == [42]


def test_create_tool_invalid_type(monkeypatch):
    with pytest.raises(TypeError):
        tool = create_tool(
            name="invalid_type_tool",
            method="GET",
            url_template="https://api.com/data",
            param_mapping={"count": {"type": "int", "for": "params"}},
        )
        tool.invoke({"count": "not_an_int"})


@pytest.mark.parametrize(
    "input_obj, listpath, expected",
    [
        ({"a": {"b": 1}}, ["a", "b"], 1),
        ({"x": [10, 20, 30]}, ["x", 1], 20),
        ({"nested": {"array": [{"value": 42}]}}, ["nested", "array", 0, "value"], 42),
    ],
)
def test_extract_fields_basic(input_obj: Dict[str, Any], listpath: list, expected: Any):
    result = extract_fields(input_obj, listpath[:])  # pass a copy so we don't mutate
    assert result == expected


def test_extract_fields_empty_listpath():
    data = {"key": "value"}
    # If listpath is empty, the function returns the object itself
    assert extract_fields(data, []) == data


def test_extract_fields_int_index_on_non_list():
    data = {"key": "value"}
    with pytest.raises(KeyError):
        _ = extract_fields(data, [0])


def test_extract_fields_invalid_key():
    data = {"a": 1, "b": 2}
    with pytest.raises(KeyError):
        _ = extract_fields(data, ["c"])


def test_extract_fields_list_vs_non_list():
    non_list_data = {"key": "value"}
    with pytest.raises(KeyError):
        _ = extract_fields(non_list_data, [0])


def test_extract_fields_with_object_attribute():
    class SomeObject:
        def __init__(self):
            self.my_attr = "hello"

    obj = SomeObject()
    assert extract_fields(obj, ["my_attr"]) == "hello"


def test_create_tool_with_data_payload(monkeypatch):

    class MockResponse:
        def __init__(self):
            self.status_code = 200

        def json(self):
            return {"received_data": True}

    def mock_request(method, url, data=None, **kwargs):
        assert method == "POST"
        # We expect 'data' to be a dict with the parameter we set
        assert data == {"foo": "bar"}
        return MockResponse()

    monkeypatch.setattr("requests.request", mock_request)

    param_mapping = {
        "foo": {"type": "str", "for": "data"},
    }

    tool = create_tool(
        name="post_data_tool",
        method="POST",
        url_template="https://example.com/test-data-endpoint",
        param_mapping=param_mapping,
    )

    # Invoke the tool with foo="bar", which should go into the 'data' field
    result_str = tool.invoke({"foo": "bar"})
    result_list = json.loads(result_str)
    assert result_list[0]["content"]["received_data"] is True
