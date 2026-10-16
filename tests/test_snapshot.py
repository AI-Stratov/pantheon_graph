import json
from pathlib import Path

import pytest

from pantheon_graph.web.frontend import FrontendNotBuiltError
from pantheon_graph.web.snapshot import write_static_site
from tests.conftest import make_graph


def test_static_site_reads_from_snapshot(tmp_path: Path, dist: Path) -> None:
    out = tmp_path / 'site'
    write_static_site(make_graph(['zeus', 'hera'], [('zeus', 'hera', 'spouse')]), out, dist=dist)

    index = (out / 'index.html').read_text()
    assert 'window.PANTHEON_CONFIG = {"apiBase": "", "snapshot": "graph.json"};' in index

    snapshot = json.loads((out / 'graph.json').read_text())
    assert [node['id'] for node in snapshot['nodes']] == ['zeus', 'hera']
    assert snapshot['edges'][0]['kind'] == 'spouse'
    assert (out / 'assets' / 'app.js').is_file()
    assert (out / '.nojekyll').is_file()


def test_static_site_requires_built_ui(tmp_path: Path) -> None:
    with pytest.raises(FrontendNotBuiltError):
        write_static_site(make_graph(['zeus']), tmp_path / 'site', dist=tmp_path / 'missing')
