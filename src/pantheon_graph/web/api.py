from datetime import UTC, datetime
from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query, Response, status

from pantheon_graph.application.service import GraphService, HealthStatus
from pantheon_graph.web.schemas import (
    GraphSchema,
    HealthSchema,
    NodeSchema,
    RefreshSchema,
    StatsSchema,
)

health_router = APIRouter(tags=['health'], route_class=DishkaRoute)
graph_router = APIRouter(prefix='/api/graph', tags=['graph'], route_class=DishkaRoute)


@health_router.get('/health', responses={503: {'model': HealthSchema}})
async def health(service: FromDishka[GraphService], response: Response) -> HealthSchema:
    """Cache and source availability; 503 when the graph cannot be served."""
    report = await service.health()
    if report.status is HealthStatus.DOWN:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthSchema(
        status=report.status,
        cache=report.cache,
        sources=report.sources,
        checked_at=datetime.now(UTC),
    )


@graph_router.get('')
async def get_graph(service: FromDishka[GraphService]) -> GraphSchema:
    """The whole aggregated graph."""
    return GraphSchema.model_validate(await service.graph())


@graph_router.post('/refresh')
async def refresh_graph(service: FromDishka[GraphService]) -> RefreshSchema:
    """Reload every source, bypassing and then updating the cache."""
    graph = await service.refresh()
    return RefreshSchema(
        nodes=len(graph.nodes), edges=len(graph.edges), refreshed_at=datetime.now(UTC)
    )


@graph_router.get('/stats')
async def get_stats(service: FromDishka[GraphService]) -> StatsSchema:
    """Node and edge counts grouped by kind."""
    return StatsSchema.model_validate(await service.stats())


@graph_router.get('/search')
async def search_nodes(
    service: FromDishka[GraphService],
    q: Annotated[str, Query(min_length=1, max_length=100, description='Text to find in labels')],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[NodeSchema]:
    """Case-insensitive search by label; prefix matches come first."""
    return [NodeSchema.model_validate(node) for node in await service.search(q, limit)]


@graph_router.get('/relationships')
async def get_relationships(
    service: FromDishka[GraphService],
    node: Annotated[str | None, Query(description='Node ID at either end of the edge')] = None,
    source: Annotated[str | None, Query(description='Source node ID')] = None,
    target: Annotated[str | None, Query(description='Target node ID')] = None,
    kind: Annotated[str | None, Query(description='Edge kind, e.g. parent or spouse')] = None,
    label: Annotated[str | None, Query(description='Edge label, e.g. mother')] = None,
) -> GraphSchema:
    """Edges matching every given filter, with the nodes they connect."""
    graph = await service.relationships(
        node=node, source=source, target=target, kind=kind, label=label
    )
    return GraphSchema.model_validate(graph)


@graph_router.get('/nodes/{node_id}', responses={404: {'description': 'Unknown node'}})
async def get_neighbourhood(
    service: FromDishka[GraphService],
    node_id: str,
    depth: Annotated[int, Query(ge=1, le=3, description='How many hops to include')] = 1,
) -> GraphSchema:
    """The node together with everything within ``depth`` hops of it."""
    return GraphSchema.model_validate(await service.neighbourhood(node_id, depth))
