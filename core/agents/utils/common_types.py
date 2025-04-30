from typing import TypedDict


class Evidence(TypedDict):
    name: str
    args: dict
    # anything with a simple string representation that can be fed into LLM
    result: str | dict | list


# Packages a claim with its evidence, label, and justification
class Analysis(TypedDict):
    claim: str
    label: str
    justification: str
    evidence: list[Evidence]
