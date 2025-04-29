from typing import TypedDict


class Evidence(TypedDict):
    """
    An item of evidence related to a claim.
    name: Name of the tool that produced the evidence
    args: Arguments passed to the tool
    result: Result of the tool
    source: Source of the evidence (e.g., URL, tool name)
    """
    name: str
    args: dict
    content: str | dict | list
    source: str

# Packages a claim with its evidence, label, and justification


class Analysis(TypedDict):
    claim: str
    label: str
    justification: str
    evidence: list[Evidence]
