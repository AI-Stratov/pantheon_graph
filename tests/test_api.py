from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get('/health')

    assert response.status_code == 200
    assert response.json() | {'checked_at': None} == {
        'status': 'ok',
        'cache': True,
        'sources': {'memory': True},
        'checked_at': None,
    }


def test_graph(client: TestClient) -> None:
    data = client.get('/api/graph').json()

    ids = {node['id'] for node in data['nodes']}
    assert {'zeus', 'hera', 'athena'} <= ids
    assert all(edge['source'] in ids and edge['target'] in ids for edge in data['edges'])
    assert data['nodes'][0].keys() == {'id', 'label', 'kind', 'properties'}


def test_refresh(client: TestClient) -> None:
    body = client.post('/api/graph/refresh').json()

    assert body['nodes'] > 0
    assert body['edges'] > 0


def test_stats(client: TestClient) -> None:
    stats = client.get('/api/graph/stats').json()

    assert stats['nodes'] == sum(stats['node_kinds'].values())
    assert set(stats['edge_kinds']) == {'parent', 'spouse', 'sibling'}


def test_search(client: TestClient) -> None:
    labels = [node['label'] for node in client.get('/api/graph/search?q=he').json()]

    assert labels[:3] == ['Hera', 'Hestia', 'Hephaestus']  # prefix matches in dataset order
    assert client.get('/api/graph/search?q=').status_code == 422


def test_relationships(client: TestClient) -> None:
    data = client.get('/api/graph/relationships', params={'node': 'zeus', 'kind': 'spouse'}).json()

    assert {node['id'] for node in data['nodes']} == {'zeus', 'hera', 'metis'}


def test_neighbourhood(client: TestClient) -> None:
    data = client.get('/api/graph/nodes/athena').json()

    assert {node['id'] for node in data['nodes']} == {'athena', 'zeus', 'metis'}
    assert client.get('/api/graph/nodes/zeus', params={'depth': 9}).status_code == 422


def test_unknown_node_is_404(client: TestClient) -> None:
    response = client.get('/api/graph/nodes/odin')

    assert response.status_code == 404
    assert response.json() == {'detail': "Node 'odin' not found"}


def test_index_injects_api_base(client: TestClient) -> None:
    page = client.get('/')

    assert page.status_code == 200
    assert 'window.PANTHEON_CONFIG = {"apiBase": "", "snapshot": null};' in page.text
    for asset in (
        'styles.css',
        'favicon.svg',
        'js/main.js',
        'js/api.js',
        'js/theme.js',
        'js/family-tree.js',
    ):
        assert client.get(f'/static/{asset}').status_code == 200, asset


def test_path(client: TestClient) -> None:
    data = client.get('/api/graph/path', params={'source': 'hephaestus', 'target': 'hermes'}).json()

    assert [node['id'] for node in data['nodes']] == ['hephaestus', 'hera', 'zeus', 'hermes']
    assert len(data['edges']) == 3


def test_path_unknown_node(client: TestClient) -> None:
    response = client.get('/api/graph/path', params={'source': 'zeus', 'target': 'odin'})

    assert response.status_code == 404
