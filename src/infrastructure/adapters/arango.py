from anyio import to_thread
from arango import ArangoClient  # type: ignore

from application.services import GraphAdapter
from core.config import ArangoConfig
from domain.models import Edge, Graph, Node


class ArangoAdapter(GraphAdapter):
    """ArangoDB adapter.

    Supports two modes:
    - Explicit collections: vertex_collection + edge_collection
    - Graph name: iterate vertex/edge collections from a named graph

    Note: python-arango is synchronous; we offload I/O to a threadpool to keep the event loop responsive.
    """

    def __init__(self, cfg: ArangoConfig):
        self._cfg = cfg
        self._client = ArangoClient(hosts=cfg.url)
        self._db = self._client.db(cfg.db, username=cfg.user, password=cfg.password)

    async def get_graph(self) -> Graph:
        # Prepare collections to query (sync, trivial)
        if self._cfg.vertex_collection and self._cfg.edge_collection:
            v_cols = [self._cfg.vertex_collection]
            e_cols = [self._cfg.edge_collection]
        elif self._cfg.graph:
            graph = self._db.graph(self._cfg.graph)
            edge_defs = graph.edge_definitions()
            v_set: set[str] = set()
            e_cols = [d["edge_collection"] for d in edge_defs]
            for d in edge_defs:
                v_set.update(d.get("from_vertex_collections", []))
                v_set.update(d.get("to_vertex_collections", []))
            v_cols = list(v_set)
        else:
            # nothing configured
            return Graph(nodes=[], edges=[])

        def _load_vertices() -> dict[str, Node]:
            nodes: dict[str, Node] = {}
            for coll in v_cols:
                cursor = self._db.aql.execute(f"FOR v IN {coll} LIMIT 1000 RETURN v")
                for doc in cursor:  # type: ignore[reportUnknownVariableType]
                    _id = doc.get("_id")
                    if not _id or _id in nodes:
                        continue
                    label = str(doc.get("name") or doc.get("label") or _id.split("/")[-1])
                    node_type = _id.split("/")[0]
                    props = {k: v for k, v in doc.items() if not k.startswith("_")}
                    nodes[_id] = Node(id=_id, label=label, type=node_type, props=props)
            return nodes

        def _load_edges() -> list[Edge]:
            edges: list[Edge] = []
            for coll in e_cols:
                cursor = self._db.aql.execute(f"FOR e IN {coll} LIMIT 2000 RETURN e")
                for doc in cursor:  # type: ignore[reportUnknownVariableType]
                    _id = doc.get("_id")
                    _from = doc.get("_from")
                    _to = doc.get("_to")
                    if not (_id and _from and _to):
                        continue
                    label = str(doc.get("label") or coll)
                    etype = coll
                    props = {k: v for k, v in doc.items() if not k.startswith("_")}
                    edges.append(Edge(id=_id, source=_from, target=_to, label=label, type=etype, props=props))
            return edges

        # Offload blocking I/O to threadpool via zero-arg lambdas
        nodes = await to_thread.run_sync(lambda: _load_vertices())
        edges = await to_thread.run_sync(lambda: _load_edges())
        return Graph(nodes=list(nodes.values()), edges=edges)
