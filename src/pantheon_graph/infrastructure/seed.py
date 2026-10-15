"""Load a graph into Neo4j or ArangoDB, e.g. the bundled dataset for a local demo."""

import logging
from typing import Any, LiteralString

from pantheon_graph.config import ArangoSettings, Neo4jSettings
from pantheon_graph.domain import Graph, Relation

logger = logging.getLogger(__name__)

_NODES_CYPHER: LiteralString = """
UNWIND $nodes AS node
MERGE (d:Deity {id: node.id})
SET d += node.properties, d.name = node.label, d.kind = node.kind
"""

_EDGES_CYPHER: dict[str, LiteralString] = {
    Relation.PARENT: """
        UNWIND $edges AS edge
        MATCH (a:Deity {id: edge.source})
        MATCH (b:Deity {id: edge.target})
        MERGE (a)-[r:PARENT_OF {id: edge.id}]->(b)
        SET r.kind = edge.kind, r.label = edge.label
    """,
    Relation.SPOUSE: """
        UNWIND $edges AS edge
        MATCH (a:Deity {id: edge.source})
        MATCH (b:Deity {id: edge.target})
        MERGE (a)-[r:SPOUSE_OF {id: edge.id}]->(b)
        SET r.kind = edge.kind, r.label = edge.label
    """,
    Relation.SIBLING: """
        UNWIND $edges AS edge
        MATCH (a:Deity {id: edge.source})
        MATCH (b:Deity {id: edge.target})
        MERGE (a)-[r:SIBLING_OF {id: edge.id}]->(b)
        SET r.kind = edge.kind, r.label = edge.label
    """,
}

_UPSERT_AQL = 'FOR doc IN @docs UPSERT {_key: doc._key} INSERT doc REPLACE doc IN @@collection'


def _properties(raw: Any) -> dict[str, Any]:
    # "source" describes where a record was read from, so it is not stored
    return {key: value for key, value in raw.items() if key != 'source'}


async def seed_neo4j(graph: Graph, settings: Neo4jSettings) -> None:
    from neo4j import AsyncGraphDatabase

    auth = (settings.user, settings.password.get_secret_value())
    driver = AsyncGraphDatabase.driver(
        settings.uri, auth=auth, connection_timeout=settings.connect_timeout
    )
    async with driver:
        await driver.verify_connectivity()  # fail fast instead of retrying writes for minutes
        await driver.execute_query(
            'CREATE CONSTRAINT deity_id IF NOT EXISTS FOR (d:Deity) REQUIRE d.id IS UNIQUE',
            database_=settings.database,
        )
        nodes = [
            {
                'id': node.id,
                'label': node.label,
                'kind': node.kind,
                'properties': _properties(node.properties),
            }
            for node in graph.nodes
        ]
        await driver.execute_query(_NODES_CYPHER, {'nodes': nodes}, database_=settings.database)

        for relation, query in _EDGES_CYPHER.items():
            edges = [
                {
                    'id': edge.id,
                    'source': edge.source,
                    'target': edge.target,
                    'kind': edge.kind,
                    'label': edge.label,
                }
                for edge in graph.edges
                if edge.kind == relation
            ]
            await driver.execute_query(query, {'edges': edges}, database_=settings.database)
    logger.info('Seeded Neo4j with %d nodes, %d edges', len(graph.nodes), len(graph.edges))


async def seed_arango(
    graph: Graph,
    settings: ArangoSettings,
    *,
    vertex_collection: str = 'deities',
    edge_collection: str = 'relations',
) -> None:
    from arangoasync import ArangoClient
    from arangoasync.auth import Auth

    graph_name = settings.graph or 'pantheon'
    auth = Auth(username=settings.user, password=settings.password.get_secret_value())
    async with ArangoClient(hosts=settings.url) as client:
        db = await client.db(settings.database, auth=auth)
        if not await db.has_graph(graph_name):
            await db.create_graph(
                graph_name,
                edge_definitions=[
                    {
                        'collection': edge_collection,
                        'from': [vertex_collection],
                        'to': [vertex_collection],
                    }
                ],
            )

        vertices = [
            {'_key': node.id, 'name': node.label, 'kind': node.kind, **_properties(node.properties)}
            for node in graph.nodes
        ]
        edges = [
            {
                '_key': edge.id,
                '_from': f'{vertex_collection}/{edge.source}',
                '_to': f'{vertex_collection}/{edge.target}',
                'kind': edge.kind,
                'label': edge.label,
            }
            for edge in graph.edges
        ]
        for collection, docs in ((vertex_collection, vertices), (edge_collection, edges)):
            await db.aql.execute(_UPSERT_AQL, bind_vars={'docs': docs, '@collection': collection})
    logger.info('Seeded ArangoDB with %d nodes, %d edges', len(graph.nodes), len(graph.edges))
