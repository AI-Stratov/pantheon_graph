from __future__ import annotations

import itertools
from collections import Counter, defaultdict, deque
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any

from pantheon_graph.domain.errors import NodeNotFoundError, PathNotFoundError

type Properties = Mapping[str, Any]


@dataclass(frozen=True, slots=True, kw_only=True)
class Node:
    id: str
    label: str
    kind: str | None = None
    properties: Properties = field(default_factory=dict, hash=False)


@dataclass(frozen=True, slots=True, kw_only=True)
class Edge:
    id: str
    source: str
    target: str
    kind: str
    label: str | None = None
    properties: Properties = field(default_factory=dict, hash=False)

    def touches(self, node_id: str) -> bool:
        return node_id in (self.source, self.target)


@dataclass(frozen=True, slots=True, kw_only=True)
class GraphStats:
    nodes: int
    edges: int
    node_kinds: Mapping[str, int]
    edge_kinds: Mapping[str, int]


@dataclass(frozen=True)
class Graph:
    """Immutable snapshot of nodes and the edges between them.

    Every operation returns a new graph, so snapshots can be cached and
    shared between requests safely.
    """

    nodes: tuple[Node, ...] = ()
    edges: tuple[Edge, ...] = ()

    @classmethod
    def build(cls, nodes: Iterable[Node] = (), edges: Iterable[Edge] = ()) -> Graph:
        return cls(tuple(nodes), tuple(edges))

    @classmethod
    def merge(cls, graphs: Iterable[Graph]) -> Graph:
        """Union of graphs; on ID clashes the later graph wins, order is preserved."""
        nodes: dict[str, Node] = {}
        edges: dict[str, Edge] = {}
        for graph in graphs:
            nodes.update((node.id, node) for node in graph.nodes)
            edges.update((edge.id, edge) for edge in graph.edges)
        return cls(tuple(nodes.values()), tuple(edges.values())).without_dangling_edges()

    @cached_property
    def _nodes_by_id(self) -> Mapping[str, Node]:
        return {node.id: node for node in self.nodes}

    @cached_property
    def _adjacency(self) -> Mapping[str, frozenset[str]]:
        neighbours: defaultdict[str, set[str]] = defaultdict(set)
        for edge in self.edges:
            neighbours[edge.source].add(edge.target)
            neighbours[edge.target].add(edge.source)
        return {node_id: frozenset(ids) for node_id, ids in neighbours.items()}

    def __contains__(self, node_id: object) -> bool:
        return node_id in self._nodes_by_id

    def node(self, node_id: str) -> Node:
        try:
            return self._nodes_by_id[node_id]
        except KeyError:
            raise NodeNotFoundError(node_id) from None

    def edges_of(self, node_id: str) -> tuple[Edge, ...]:
        return tuple(edge for edge in self.edges if edge.touches(node_id))

    def induced(self, node_ids: Iterable[str]) -> Graph:
        """Subgraph made of the given nodes and every edge between them."""
        keep = frozenset(node_ids)
        return Graph(
            tuple(node for node in self.nodes if node.id in keep),
            tuple(edge for edge in self.edges if edge.source in keep and edge.target in keep),
        )

    def without_dangling_edges(self) -> Graph:
        """Drop edges whose endpoints are missing, e.g. cut off by a source query limit."""
        if all(edge.source in self and edge.target in self for edge in self.edges):
            return self
        return Graph(
            self.nodes,
            tuple(edge for edge in self.edges if edge.source in self and edge.target in self),
        )

    def neighbourhood(self, node_id: str, depth: int = 1) -> Graph:
        """Nodes within ``depth`` hops of ``node_id``, ignoring edge direction."""
        self.node(node_id)  # raises for unknown IDs
        visited = {node_id}
        frontier = {node_id}
        for _ in range(depth):
            frontier = {
                neighbour
                for current in frontier
                for neighbour in self._adjacency.get(current, ())
                if neighbour not in visited
            }
            if not frontier:
                break
            visited |= frontier
        return self.induced(visited)

    def shortest_path(self, source: str, target: str) -> Graph:
        """Fewest-hops chain from ``source`` to ``target``, ignoring edge direction.

        The result lists nodes and edges in walking order, so it reads as
        "source -edge-> node -edge-> ... target".

        Raises:
            NodeNotFoundError: If either endpoint is unknown
            PathNotFoundError: If the endpoints are not connected
        """
        self.node(source)
        self.node(target)

        previous: dict[str, str | None] = {source: None}
        queue = deque([source])
        while queue and target not in previous:
            current = queue.popleft()
            for neighbour in sorted(self._adjacency.get(current, ())):  # sorted: stable answer
                if neighbour not in previous:
                    previous[neighbour] = current
                    queue.append(neighbour)

        if target not in previous:
            raise PathNotFoundError(source, target)

        chain = [target]
        while (step := previous[chain[-1]]) is not None:
            chain.append(step)
        chain.reverse()

        edges = tuple(self._edge_between(a, b) for a, b in itertools.pairwise(chain))
        return Graph(tuple(self.node(node_id) for node_id in chain), edges)

    def _edge_between(self, first: str, second: str) -> Edge:
        return next(edge for edge in self.edges if {edge.source, edge.target} == {first, second})

    def filter_edges(
        self,
        *,
        node: str | None = None,
        source: str | None = None,
        target: str | None = None,
        kind: str | None = None,
        label: str | None = None,
    ) -> Graph:
        """Edges matching every given criterion, plus the nodes they connect.

        ``node`` matches either endpoint, which is what you want for symmetric
        relations whose endpoint order is arbitrary.
        """
        edges = tuple(
            edge
            for edge in self.edges
            if (node is None or edge.touches(node))
            and (source is None or edge.source == source)
            and (target is None or edge.target == target)
            and (kind is None or edge.kind == kind)
            and (label is None or edge.label == label)
        )
        connected = {edge.source for edge in edges} | {edge.target for edge in edges}
        return Graph(tuple(node for node in self.nodes if node.id in connected), edges)

    def search(self, query: str, limit: int = 20) -> list[Node]:
        """Case-insensitive label search: exact ID and prefix matches rank first."""
        needle = query.strip().casefold()
        if not needle:
            return []

        def rank(node: Node) -> int | None:
            label = node.label.casefold()
            if node.id.casefold() == needle or label.startswith(needle):
                return 0
            if needle in label:
                return 1
            return None

        ranked = [(score, node) for node in self.nodes if (score := rank(node)) is not None]
        ranked.sort(key=lambda item: item[0])  # stable: keeps graph order within a rank
        return [node for _, node in ranked[:limit]]

    def stats(self) -> GraphStats:
        return GraphStats(
            nodes=len(self.nodes),
            edges=len(self.edges),
            node_kinds=dict(Counter(node.kind or 'unknown' for node in self.nodes).most_common()),
            edge_kinds=dict(Counter(edge.kind for edge in self.edges).most_common()),
        )
