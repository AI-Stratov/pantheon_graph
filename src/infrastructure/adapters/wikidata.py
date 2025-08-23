import re
from typing import final, Any

import httpx

from application.services import GraphAdapterInterface
from core.constants import (
    WikidataProperties,
    WikidataEndpoints,
    DatabaseLimits,
    HttpDefaults,
    NodeTypes,
    RelationshipTypes
)
from domain.models import Edge, Graph, Node

# Compiled regex for better performance
WIKIDATA_QID_PATTERN = re.compile(r"/(Q\d+)$")

# Mapping from Wikidata properties to relationship types
PROPERTY_TO_RELATIONSHIP = {
    WikidataProperties.SPOUSE: RelationshipTypes.SPOUSE,
    WikidataProperties.FATHER: RelationshipTypes.FATHER,
    WikidataProperties.MOTHER: RelationshipTypes.MOTHER,
    WikidataProperties.SIBLING: RelationshipTypes.SIBLING,
}


@final
class WikidataAdapter(GraphAdapterInterface):  # type: ignore[misc]
    """Wikidata SPARQL adapter for fetching Greek deity relationships.

    This adapter queries Wikidata's SPARQL endpoint to retrieve information
    about Greek deities and their family relationships, including spouses,
    parents, and siblings.

    Attributes:
        _endpoint: SPARQL endpoint URL
        _user_agent: HTTP User-Agent string for requests
        _client: HTTP client for making requests
    """

    def __init__(
        self,
        endpoint: str = WikidataEndpoints.DEFAULT_SPARQL_ENDPOINT,
        user_agent: str = WikidataEndpoints.DEFAULT_USER_AGENT
    ) -> None:
        """Initialize Wikidata adapter with endpoint configuration.

        Args:
            endpoint: SPARQL endpoint URL
            user_agent: User-Agent string for HTTP requests
        """
        self._endpoint = endpoint
        self._user_agent = user_agent
        self._client: httpx.AsyncClient | None = None

    async def get_graph(self) -> Graph:
        """Retrieve graph data from Wikidata SPARQL endpoint.

        Returns:
            Graph containing Greek deities and their relationships

        Raises:
            Exception: If SPARQL queries fail or network issues occur
        """
        async with self._get_client() as client:
            self._client = client
            nodes = await self._fetch_deity_nodes()
            edges = await self._fetch_relationship_edges(list(nodes.keys()))

        return Graph(nodes=list(nodes.values()), edges=edges)

    async def health_check(self) -> bool:
        """Check if Wikidata SPARQL endpoint is accessible.

        Returns:
            True if endpoint responds to a simple test query
        """
        try:
            test_query = "SELECT (COUNT(*) as ?count) WHERE { ?s ?p ?o } LIMIT 1"
            async with self._get_client() as client:
                response = await client.get(
                    self._endpoint,
                    params={"query": test_query}
                )
                return response.status_code == 200
        except Exception:
            return False

    def _get_client(self) -> httpx.AsyncClient:
        """Create configured HTTP client for SPARQL requests.

        Returns:
            Configured AsyncClient instance
        """
        headers = {
            "Accept": "application/sparql-results+json",
            "User-Agent": self._user_agent,
        }
        return httpx.AsyncClient(
            timeout=HttpDefaults.DEFAULT_TIMEOUT_SECONDS,
            headers=headers
        )

    async def _fetch_deity_nodes(self) -> dict[str, Node]:
        """Fetch Greek deity nodes from Wikidata.

        Returns:
            Dictionary mapping QID to Node objects
        """
        sparql_query = f"""
        SELECT ?item ?itemLabel WHERE {{
          ?item wdt:{WikidataProperties.INSTANCE_OF} wd:{WikidataProperties.GREEK_DEITY} .
          SERVICE wikibase:label {{ 
            bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". 
          }}
        }} LIMIT {DatabaseLimits.WIKIDATA_DEITY_LIMIT}
        """

        data = await self._execute_sparql_query(sparql_query)
        nodes: dict[str, Node] = {}

        for binding in data.get("results", {}).get("bindings", []):
            item_uri = binding.get("item", {}).get("value")
            label = binding.get("itemLabel", {}).get("value")

            if not item_uri or not label:
                continue

            qid = self._extract_qid(item_uri)
            if not qid:
                continue

            nodes[qid] = Node(
                id=qid,
                label=label,
                type=NodeTypes.DEITY,
                props={"source": "wikidata"}
            )

        return nodes

    async def _fetch_relationship_edges(
        self,
        known_entity_ids: set[str] | list[str]
    ) -> list[Edge]:
        """Fetch relationship edges between known entities.

        Args:
            known_entity_ids: Set of known entity QIDs to filter relationships

        Returns:
            List of Edge objects representing relationships
        """
        if not known_entity_ids:
            return []

        # Build VALUES clause for filtering
        entity_values = " ".join(f"wd:{qid}" for qid in known_entity_ids)
        property_values = " ".join(
            f"wdt:{prop}" for prop in PROPERTY_TO_RELATIONSHIP.keys()
        )

        sparql_query = f"""
        SELECT ?source ?target ?property WHERE {{
          VALUES ?source {{ {entity_values} }}
          VALUES ?property {{ {property_values} }}
          ?source ?property ?target .
          VALUES ?target {{ {entity_values} }}
        }} LIMIT {DatabaseLimits.WIKIDATA_RELATIONSHIP_LIMIT}
        """

        data = await self._execute_sparql_query(sparql_query)
        edges: list[Edge] = []

        for binding in data.get("results", {}).get("bindings", []):
            source_qid = self._extract_qid(binding.get("source", {}).get("value"))
            target_qid = self._extract_qid(binding.get("target", {}).get("value"))
            property_uri = binding.get("property", {}).get("value")

            if not (source_qid and target_qid and property_uri):
                continue

            property_id = property_uri.split("/")[-1]
            relationship_type = PROPERTY_TO_RELATIONSHIP.get(property_id, property_id)

            edge_id = f"{source_qid}-{target_qid}-{property_id}"
            edges.append(
                Edge(
                    id=edge_id,
                    source=source_qid,
                    target=target_qid,
                    label=relationship_type,
                    type=property_id,
                    props={"source": "wikidata"}
                )
            )

        return edges

    async def _execute_sparql_query(self, query: str) -> dict[str, Any]:
        """Execute SPARQL query against Wikidata endpoint.

        Args:
            query: SPARQL query string

        Returns:
            Parsed JSON response from the endpoint

        Raises:
            httpx.HTTPStatusError: If the request fails
        """
        if not self._client:
            raise RuntimeError("HTTP client not initialized")

        response = await self._client.get(
            self._endpoint,
            params={"query": query}
        )
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result

    @staticmethod
    def _extract_qid(uri: str | None) -> str | None:
        """Extract Wikidata QID from a URI.

        Args:
            uri: Wikidata entity URI

        Returns:
            QID string or None if not found
        """
        if not uri:
            return None

        match = WIKIDATA_QID_PATTERN.search(uri)
        return match.group(1) if match else None
