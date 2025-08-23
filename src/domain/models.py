from typing import Any

from pydantic import BaseModel, Field


class Node(BaseModel):
    id: str
    label: str
    type: str | None = None
    props: dict[str, Any] = Field(default_factory=dict)


class Edge(BaseModel):
    id: str
    source: str
    target: str
    label: str | None = None
    type: str | None = None
    props: dict[str, Any] = Field(default_factory=dict)


class Graph(BaseModel):
    nodes: list[Node] = Field(default_factory=list)
    edges: list[Edge] = Field(default_factory=list)
