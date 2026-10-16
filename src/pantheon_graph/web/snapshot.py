"""Static, backend-free build of the UI, e.g. for GitHub Pages."""

import shutil
from pathlib import Path

from pantheon_graph.domain import Graph
from pantheon_graph.web.frontend import DIST, render_index
from pantheon_graph.web.schemas import GraphSchema

SNAPSHOT_FILE = 'graph.json'


def write_static_site(graph: Graph, out_dir: Path, *, dist: Path = DIST) -> None:
    """Copy the built UI to ``out_dir`` and make it read a JSON snapshot of ``graph``."""
    index = render_index(dist, snapshot=SNAPSHOT_FILE)  # fails early if the UI is not built
    shutil.copytree(dist, out_dir, dirs_exist_ok=True)
    (out_dir / 'index.html').write_text(index, encoding='utf-8')
    (out_dir / SNAPSHOT_FILE).write_bytes(
        GraphSchema.model_validate(graph).model_dump_json().encode()
    )
    (out_dir / '.nojekyll').touch()  # serve files as-is on GitHub Pages
