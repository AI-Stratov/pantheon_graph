from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from pantheon_graph.application.service import HealthStatus


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)


class NodeSchema(Schema):
    id: str
    label: str
    kind: str | None
    properties: dict[str, Any]


class EdgeSchema(Schema):
    id: str
    source: str = Field(description='ID of the source node; parent edges point parent -> child')
    target: str
    kind: str
    label: str | None
    properties: dict[str, Any]


class GraphSchema(Schema):
    nodes: list[NodeSchema]
    edges: list[EdgeSchema]


class StatsSchema(Schema):
    nodes: int
    edges: int
    node_kinds: dict[str, int]
    edge_kinds: dict[str, int]


class RefreshSchema(Schema):
    nodes: int
    edges: int
    refreshed_at: datetime


class HealthSchema(Schema):
    status: HealthStatus
    cache: bool
    sources: dict[str, bool]
    checked_at: datetime
