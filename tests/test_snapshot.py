import json
from pathlib import Path

from pantheon_graph.web.snapshot import write_static_site
from tests.conftest import make_graph


def test_static_site_reads_from_snapshot(tmp_path: Path) -> None:
    write_static_site(make_graph(['zeus', 'hera'], [('zeus', 'hera', 'spouse')]), tmp_path)

    index = (tmp_path / 'index.html').read_text()
    assert 'window.PANTHEON_CONFIG = {"apiBase": "", "snapshot": "graph.json"};' in index

    snapshot = json.loads((tmp_path / 'graph.json').read_text())
    assert [node['id'] for node in snapshot['nodes']] == ['zeus', 'hera']
    assert snapshot['edges'][0]['kind'] == 'spouse'

    assert (tmp_path / 'static' / 'js' / 'main.js').is_file()
    assert not (tmp_path / 'static' / 'index.html').exists()
