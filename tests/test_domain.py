import pytest

from pantheon_graph.domain import Edge, Graph, Node, NodeNotFoundError, PathNotFoundError
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


def test_shortest_path_walks_edges_in_order() -> None:
    graph = make_graph(
        ['hera', 'zeus', 'hermes', 'hephaestus', 'maia'],
        [
            ('hera', 'hephaestus', 'parent'),
            ('zeus', 'hera', 'spouse'),
            ('zeus', 'hermes', 'parent'),
            ('maia', 'hermes', 'parent'),
        ],
    )

    path = graph.shortest_path('hephaestus', 'hermes')

    assert [node.id for node in path.nodes] == ['hephaestus', 'hera', 'zeus', 'hermes']
    assert [edge.kind for edge in path.edges] == ['parent', 'spouse', 'parent']


def test_shortest_path_to_itself() -> None:
    path = make_graph(['zeus']).shortest_path('zeus', 'zeus')

    assert [node.id for node in path.nodes] == ['zeus']
    assert path.edges == ()


def test_shortest_path_errors() -> None:
    graph = make_graph(['zeus', 'odin'])

    with pytest.raises(PathNotFoundError):
        graph.shortest_path('zeus', 'odin')
    with pytest.raises(NodeNotFoundError):
        graph.shortest_path('zeus', 'thor')


def test_merge_folds_same_figure_from_another_source() -> None:
    bundled = Graph.build(
        [
            Node(
                id='zeus',
                label='Zeus',
                kind='olympian',
                properties={'source': 'memory', 'roman': 'Jupiter'},
            ),
            Node(id='hera', label='Hera', kind='olympian', properties={'source': 'memory'}),
            Node(id='ares', label='Ares', kind='olympian', properties={'source': 'memory'}),
        ],
        [
            Edge(id='hera-zeus-spouse', source='hera', target='zeus', kind='spouse'),
            Edge(
                id='zeus-ares-parent', source='zeus', target='ares', kind='parent', label='parent'
            ),
        ],
    )
    wikidata = Graph.build(
        [
            Node(
                id='Q34201',
                label='zeus',
                kind='deity',
                properties={'source': 'wikidata', 'gender': 'male'},
            ),
            Node(id='Q35500', label='Hera', kind='deity', properties={'source': 'wikidata'}),
            Node(id='Q40901', label='Ares', kind='deity', properties={'source': 'wikidata'}),
            Node(id='Q1', label='Eris', kind='deity', properties={'source': 'wikidata'}),
        ],
        [
            # same marriage, other direction; same fatherhood with a more specific label
            Edge(id='Q34201-Q35500-spouse', source='Q34201', target='Q35500', kind='spouse'),
            Edge(
                id='Q34201-Q40901-parent',
                source='Q34201',
                target='Q40901',
                kind='parent',
                label='father',
            ),
            Edge(id='Q35500-Q1-parent', source='Q35500', target='Q1', kind='parent'),
        ],
    )

    merged = Graph.merge([bundled, wikidata])

    assert [node.id for node in merged.nodes] == ['zeus', 'hera', 'ares', 'Q1']
    zeus = merged.node('zeus')
    assert zeus.kind == 'deity'
    assert zeus.properties == {
        'roman': 'Jupiter',
        'gender': 'male',
        'sources': ['memory', 'wikidata'],
    }
    assert len(merged.edges) == 3
    fatherhood = merged.filter_edges(source='zeus', target='ares').edges[0]
    assert (fatherhood.id, fatherhood.label) == ('zeus-ares-parent', 'father')
    assert merged.filter_edges(source='hera', target='Q1').edges


def test_merge_keeps_distinct_nodes_within_one_source() -> None:
    graph = Graph.build([Node(id='a', label='Eros'), Node(id='b', label='Eros')])

    assert len(Graph.merge([graph]).nodes) == 2
