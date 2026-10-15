import os
from collections.abc import Iterator, Sequence

import pytest
from fastapi.testclient import TestClient

from pantheon_graph.config import Settings
from pantheon_graph.domain import Edge, Graph, Node
from pantheon_graph.web.app import create_app


@pytest.fixture
def anyio_backend() -> str:
    return 'asyncio'


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    # Isolate tests from the developer's environment and .env file
    for name in [name for name in os.environ if name.startswith('PANTHEON_')]:
        monkeypatch.delenv(name)
    return Settings(_env_file=None)


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client


def make_graph(node_ids: Sequence[str], edges: Sequence[tuple[str, str, str]] = ()) -> Graph:
    return Graph.build(
        [Node(id=node_id, label=node_id.title(), kind='god') for node_id in node_ids],
        [
            Edge(id=f'{source}-{target}-{kind}', source=source, target=target, kind=kind)
            for source, target, kind in edges
        ],
    )


class StubSource:
    def __init__(self, graph: Graph | None = None, *, error: Exception | None = None) -> None:
        self.name = 'stub'
        self.graph = graph or Graph()
        self.error = error
        self.calls = 0

    async def fetch(self) -> Graph:
        self.calls += 1
        if self.error:
            raise self.error
        return self.graph

    async def ping(self) -> bool:
        if self.error:
            raise self.error
        return True
