import json
from importlib.resources import files
from typing import Any, Self

from pantheon_graph.domain import Graph, Node, Relation
from pantheon_graph.infrastructure.sources._common import relation_edge

DATASET = files(__package__) / 'data' / 'pantheon.json'


class MemorySource:
    """Serves a bundled Greek pantheon (genealogy mostly after Hesiod's Theogony)."""

    name = 'memory'

    def __init__(self, graph: Graph) -> None:
        self._graph = graph

    @classmethod
    def bundled(cls) -> Self:
        return cls(load_dataset(json.loads(DATASET.read_text(encoding='utf-8'))))

    async def fetch(self) -> Graph:
        return self._graph

    async def ping(self) -> bool:
        return True


def load_dataset(data: dict[str, Any]) -> Graph:
    nodes = [
        Node(
            id=item['id'],
            label=item['label'],
            kind=item.get('kind'),
            properties={'source': 'memory'}
            | {key: value for key, value in item.items() if key not in {'id', 'label', 'kind'}},
        )
        for item in data['nodes']
    ]
    edges = [
        relation_edge(parent, child, Relation.PARENT, source='memory')
        for family in data.get('parents', [])
        for parent in family['parents']
        for child in family['children']
    ]
    edges += [
        relation_edge(first, second, Relation.SPOUSE, source='memory')
        for first, second in data.get('spouses', [])
    ]
    edges += [
        relation_edge(first, second, Relation.SIBLING, source='memory')
        for first, second in data.get('siblings', [])
    ]
    return Graph.build(nodes, edges)
