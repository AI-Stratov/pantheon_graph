from collections.abc import Mapping
from datetime import date, datetime, time
from typing import Any

from pantheon_graph.domain import Edge, Relation

type JsonValue = str | int | float | bool | list[JsonValue] | dict[str, JsonValue] | None


def to_json(value: Any) -> JsonValue:
    """Coerce driver-specific values (temporal, spatial, bytes...) into JSON values."""
    match value:
        case None | str() | int() | float() | bool():
            return value
        case Mapping():
            return {str(key): to_json(item) for key, item in value.items()}
        case list() | tuple() | set() | frozenset():
            return [to_json(item) for item in value]
        case bytes():
            return value.hex()
        case date() | datetime() | time():
            return value.isoformat()
        case _ if callable(iso := getattr(value, 'iso_format', None)):
            return str(iso())  # neo4j.time types
        case _:
            return str(value)


def clean_properties(
    raw: Mapping[str, Any], *, skip: frozenset[str] = frozenset()
) -> dict[str, JsonValue]:
    """JSON-safe copy of a property map without system keys (``_id``, ``_rev``...)."""
    return {
        key: to_json(value)
        for key, value in raw.items()
        if not key.startswith('_') and key not in skip and value is not None
    }


def relation_edge(
    source: str, target: str, relation: Relation, /, *, label: str | None = None, **properties: Any
) -> Edge:
    """Edge with a deterministic ID; symmetric relations get a canonical endpoint order."""
    if relation.is_symmetric:
        source, target = sorted((source, target))
    return Edge(
        id=f'{source}-{target}-{relation}',
        source=source,
        target=target,
        kind=relation,
        label=label or relation,
        properties=properties,
    )
