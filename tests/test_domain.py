import pytest

from pantheon_graph.domain import Graph, NodeNotFoundError
from tests.conftest import make_graph


def test_merge_later_graph_wins_and_drops_dangling_edges() -> None:
    first = make_graph(['zeus', 'hera'], [('zeus', 'hera', 'spouse')])
    second = make_graph(['hera', 'ares'], [('hera', 'ares', 'parent'), ('ares', 'eris', 'sibling')])

    merged = Graph.merge([first, second])

    assert [node.id for node in merged.nodes] == ['zeus', 'hera', 'ares']
    assert {edge.id for edge in merged.edges} == {'zeus-hera-spouse', 'hera-ares-parent'}


def test_without_dangling_edges_is_identity_for_clean_graph() -> None:
    graph = make_graph(['zeus', 'hera'], [('zeus', 'hera', 'spouse')])

    assert graph.without_dangling_edges() is graph


def test_node_lookup() -> None:
    graph = make_graph(['zeus'])

    assert graph.node('zeus').label == 'Zeus'
    assert 'zeus' in graph
    with pytest.raises(NodeNotFoundError, match='odin'):
        graph.node('odin')


@pytest.mark.parametrize(
    ('depth', 'expected'),
    [(1, {'cronus', 'zeus', 'ares'}), (2, {'cronus', 'zeus', 'ares', 'eros'})],
)
def test_neighbourhood_depth(depth: int, expected: set[str]) -> None:
    graph = make_graph(
        ['cronus', 'zeus', 'ares', 'eros', 'gaia'],
        [('cronus', 'zeus', 'parent'), ('zeus', 'ares', 'parent'), ('ares', 'eros', 'parent')],
    )

    assert {node.id for node in graph.neighbourhood('zeus', depth).nodes} == expected


def test_filter_edges() -> None:
    graph = make_graph(
        ['zeus', 'hera', 'ares'],
        [('hera', 'zeus', 'spouse'), ('zeus', 'ares', 'parent'), ('hera', 'ares', 'parent')],
    )

    by_node = graph.filter_edges(node='zeus')
    by_direction = graph.filter_edges(source='hera', kind='parent')

    assert {edge.id for edge in by_node.edges} == {'hera-zeus-spouse', 'zeus-ares-parent'}
    assert [edge.id for edge in by_direction.edges] == ['hera-ares-parent']
    assert {node.id for node in by_direction.nodes} == {'hera', 'ares'}


def test_search_ranks_prefix_first() -> None:
    graph = make_graph(['athena', 'hephaestus', 'hera'])

    assert [node.id for node in graph.search('HE')] == ['hephaestus', 'hera', 'athena']
    assert graph.search('he', limit=1)[0].id == 'hephaestus'
    assert graph.search('  ') == []


def test_stats() -> None:
    stats = make_graph(['zeus', 'hera'], [('zeus', 'hera', 'spouse')]).stats()

    assert (stats.nodes, stats.edges) == (2, 1)
    assert stats.node_kinds == {'god': 2}
    assert stats.edge_kinds == {'spouse': 1}


def test_nodes_are_hashable_despite_properties() -> None:
    graph = make_graph(['zeus'])

    assert len(set(graph.nodes)) == 1
