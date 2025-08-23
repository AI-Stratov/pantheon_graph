from datetime import datetime, UTC
from typing import Annotated

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Query, HTTPException, status

from application.services import GraphQueryService
from domain.models import Graph
from presentation.api.schemas import ApiStatusEnum, HealthResponse, ApiStatus

router = APIRouter(tags=["graph"])


@router.get("/health/", response_model=HealthResponse)
@inject
async def health_check(svc: FromDishka[GraphQueryService]) -> HealthResponse:
    """Comprehensive health check for all graph services.

    This endpoint checks the health of all configured adapters and cache
    to provide a complete system status overview.
    """
    try:
        service_health = await svc.health_check()
        overall_healthy = all(service_health.values())

        return HealthResponse(
            status=ApiStatusEnum.OK if overall_healthy else ApiStatusEnum.ERROR,
            services=service_health,
            timestamp=datetime.now(UTC).isoformat()
        )
    except Exception as e:
        return HealthResponse(
            status=ApiStatusEnum.ERROR,
            services={},
            timestamp=datetime.now(UTC).isoformat()
        )


@router.get("/api/graph/", response_model=Graph)
@inject
async def get_graph(
        svc: FromDishka[GraphQueryService],
        refresh: Annotated[bool, Query(description="Force refresh from data adapters")] = False,
) -> Graph:
    """Retrieve the complete graph with all nodes and edges.

    Args:
        refresh: If True, bypasses cache and fetches fresh data from adapters

    Returns:
        Complete graph with nodes and edges

    Raises:
        HTTPException: If graph retrieval fails
    """
    try:
        return await svc.get_graph(refresh=refresh)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve graph: {str(e)}"
        ) from e


@router.get("/api/relationships/", response_model=Graph)
@inject
async def get_relationships(
        svc: FromDishka[GraphQueryService],
        source: Annotated[str | None, Query(description="Filter by source node ID")] = None,
        target: Annotated[str | None, Query(description="Filter by target node ID")] = None,
        edge_type: Annotated[str | None, Query(alias="type", description="Filter by edge type")] = None,
        label: Annotated[str | None, Query(description="Filter by edge label")] = None,
) -> Graph:
    """Filter graph relationships based on specified criteria.

    This endpoint allows filtering the graph to show only relationships
    that match the provided criteria. All connected nodes are included.

    Args:
        source: Filter edges by source node ID
        target: Filter edges by target node ID
        edge_type: Filter edges by type
        label: Filter edges by label

    Returns:
        Filtered graph containing matching edges and their connected nodes

    Raises:
        HTTPException: If graph retrieval or filtering fails
    """
    try:
        graph = await svc.get_graph()
        filtered_edges = graph.edges

        # Apply filters
        if source is not None:
            filtered_edges = [edge for edge in filtered_edges if edge.source == source]
        if target is not None:
            filtered_edges = [edge for edge in filtered_edges if edge.target == target]
        if edge_type is not None:
            filtered_edges = [edge for edge in filtered_edges if edge.type == edge_type]
        if label is not None:
            filtered_edges = [edge for edge in filtered_edges if edge.label == label]

        # Collect all node IDs that are connected to filtered edges
        connected_node_ids = {edge.source for edge in filtered_edges} | {edge.target for edge in filtered_edges}

        # Include only nodes that are connected to the filtered edges
        filtered_nodes = [node for node in graph.nodes if node.id in connected_node_ids]

        return Graph(nodes=filtered_nodes, edges=filtered_edges)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to filter relationships: {str(e)}"
        ) from e


@router.post("/api/graph/refresh/", response_model=ApiStatus)
@inject
async def refresh_graph(svc: FromDishka[GraphQueryService]) -> ApiStatus:
    """Force refresh of graph data from all adapters.

    This endpoint bypasses the cache and fetches fresh data from all
    configured data sources, then updates the cache with new data.

    Returns:
        Status confirming the refresh operation

    Raises:
        HTTPException: If refresh operation fails
    """
    try:
        await svc.get_graph(refresh=True)
        return ApiStatus(
            status=ApiStatusEnum.OK,
            detail=ApiStatusEnum.REFRESHED
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh graph: {str(e)}"
        ) from e


@router.get("/api/nodes/{node_id}/", response_model=Graph)
@inject
async def get_node_subgraph(
        node_id: str,
        svc: FromDishka[GraphQueryService],
        depth: Annotated[int, Query(ge=1, le=3, description="Maximum traversal depth")] = 1,
) -> Graph:
    """Get a subgraph centered on a specific node.

    This endpoint returns the specified node and all nodes within the
    specified traversal depth, along with the connecting edges.

    Args:
        node_id: ID of the central node
        depth: Maximum depth for graph traversal (1-3)

    Returns:
        Subgraph containing the node and its neighbors

    Raises:
        HTTPException: If node not found or traversal fails
    """
    try:
        graph = await svc.get_graph()

        # Check if the requested node exists
        target_node = graph.get_node_by_id(node_id)
        if not target_node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Node with ID '{node_id}' not found"
            )

        # Simple breadth-first traversal to specified depth
        visited_nodes = {node_id}
        current_level = {node_id}

        for _ in range(depth):
            next_level = set()
            for current_node_id in current_level:
                # Find all edges connected to current node
                connected_edges = graph.get_edges_for_node(current_node_id)
                for edge in connected_edges:
                    # Add neighboring nodes
                    neighbor_id = edge.target if edge.source == current_node_id else edge.source
                    if neighbor_id not in visited_nodes:
                        next_level.add(neighbor_id)
                        visited_nodes.add(neighbor_id)
            current_level = next_level
            if not current_level:
                break

        # Build subgraph with visited nodes and connecting edges
        subgraph_nodes = [node for node in graph.nodes if node.id in visited_nodes]
        subgraph_edges = [
            edge for edge in graph.edges
            if edge.source in visited_nodes and edge.target in visited_nodes
        ]

        return Graph(nodes=subgraph_nodes, edges=subgraph_edges)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get node subgraph: {str(e)}"
        ) from e
