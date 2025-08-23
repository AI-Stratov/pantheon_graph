from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Query

from application.services import GraphQueryService
from domain.models import Graph
from presentation.api.schemas import ApiStatus

router = APIRouter(tags=["graph"])


@router.get("/health/", response_model=ApiStatus)
async def health():
    return ApiStatus(status="ok")


@router.get("/api/graph/", response_model=Graph)
@inject
async def api_graph(
        svc: FromDishka[GraphQueryService],
        refresh: bool = Query(False, description="Force refresh from data adapters"),
):
    return await svc.get_graph(refresh=refresh)


@router.get("/api/relationships/", response_model=Graph)
@inject
async def api_relationships(
        svc: FromDishka[GraphQueryService],
        source: str | None = Query(None),
        target: str | None = Query(None),
        type: str | None = Query(None),
        label: str | None = Query(None),
):
    g = await svc.get_graph()
    edges = g.edges
    if source is not None:
        edges = [e for e in edges if e.source == source]
    if target is not None:
        edges = [e for e in edges if e.target == target]
    if type is not None:
        edges = [e for e in edges if e.type == type]
    if label is not None:
        edges = [e for e in edges if e.label == label]
    node_ids = {e.source for e in edges} | {e.target for e in edges}
    nodes = [n for n in g.nodes if n.id in node_ids]
    return Graph(nodes=nodes, edges=edges)


@router.post("/api/graph/refresh/", response_model=ApiStatus)
@inject
async def api_graph_refresh(svc: FromDishka[GraphQueryService]):
    await svc.get_graph(refresh=True)
    return ApiStatus(status="ok")
