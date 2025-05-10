# from typing import TypedDict, Union
from typing import Union
from typing_extensions import TypedDict
from pydantic import BaseModel, RootModel


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


class Analysis(TypedDict):
    """
    Packages a claim with its evidence, label, and justification
    """
    claim: str
    label: str
    justification: str
    evidence: list[Evidence]


class EvidenceModel(BaseModel):
    """
    Evidence model for storing evidence data.
    """
    name: str
    args: dict
    content: Union[str, dict, list]
    source: str


EvidenceListModel = RootModel[list[Evidence]]
