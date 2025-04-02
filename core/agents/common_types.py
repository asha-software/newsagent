from typing import TypedDict


class Evidence(TypedDict):
    name: str
    args: dict
    # anything with a simple string representation that can be fed into LLM
    result: str | dict | list
