import re
from dataclasses import dataclass

import httpx

from application.services import GraphAdapter
from domain.models import Edge, Graph, Node

WIKIDATA_QID_RE = re.compile(r"/(Q\d+)$")


@dataclass
class WikidataQuery:
    endpoint: str
    user_agent: str


class WikidataAdapter(GraphAdapter):
    """Wikidata adapter using SPARQL to fetch Greek deities and relationships.

    Properties included:
    - P26 spouse
    - P22 father
    - P25 mother
    - P3373 sibling
    """

    def __init__(self, endpoint: str, user_agent: str) -> None:
        self._q = WikidataQuery(endpoint=endpoint, user_agent=user_agent)

    async def get_graph(self) -> Graph:
        nodes = await self._fetch_nodes()
        edges = await self._fetch_edges(nodes.keys())
        return Graph(nodes=list(nodes.values()), edges=edges)

    async def _fetch_nodes(self) -> dict[str, Node]:
        # Instance of Greek deity (Q22989102). Limit to keep demo small.
        sparql = """
        SELECT ?item ?itemLabel WHERE {
          ?item wdt:P31 wd:Q22989102 .
          SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
        } LIMIT 400
        """
        data = await self._query(sparql)
        result: dict[str, Node] = {}
        for b in data.get("results", {}).get("bindings", []):
            uri = b.get("item", {}).get("value")
            label = b.get("itemLabel", {}).get("value")
            if not uri or not label:
                continue
            qid = self._qid(uri)
            if not qid:
                continue
            result[qid] = Node(id=qid, label=label, type="deity", props={})
        return result

    async def _fetch_edges(self, allowed: set[str] | dict_keys[str] | list[str]) -> list[Edge]:  # type: ignore[name-defined]
        # Build VALUES list for filtering to known nodes to reduce noise
        values = " ".join(f"wd:{qid}" for qid in allowed)
        if not values:
            return []
        sparql = f"""
        SELECT ?a ?b ?prop WHERE {{
          VALUES ?a {{ {values} }}
          VALUES ?prop {{ wdt:P26 wdt:P22 wdt:P25 wdt:P3373 }}
          ?a ?prop ?b .
          VALUES ?b {{ {values} }}
        }} LIMIT 4000
        """
        data = await self._query(sparql)
        edges: list[Edge] = []
        for b in data.get("results", {}).get("bindings", []):
            a = self._qid(b.get("a", {}).get("value"))
            bq = self._qid(b.get("b", {}).get("value"))
            prop = b.get("prop", {}).get("value")
            if not (a and bq and prop):
                continue
            pshort = prop.split("/")[-1]
            eid = f"{a}-{bq}-{pshort}"
            label = {
                "P26": "spouse",
                "P22": "father",
                "P25": "mother",
                "P3373": "sibling",
            }.get(pshort, pshort)
            edges.append(Edge(id=eid, source=a, target=bq, label=label, type=pshort, props={}))
        return edges

    async def _query(self, sparql: str) -> dict:
        headers = {
            "Accept": "application/sparql-results+json",
            "User-Agent": self._q.user_agent,
        }
        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            resp = await client.get(self._q.endpoint, params={"query": sparql})
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    def _qid(uri: str | None) -> str | None:
        if not uri:
            return None
        m = WIKIDATA_QID_RE.search(uri)
        return m.group(1) if m else None
