"""Static, backend-free build of the UI, e.g. for GitHub Pages."""

import shutil
from pathlib import Path

from pantheon_graph.domain import Graph
from pantheon_graph.web.frontend import STATIC, render_index
from pantheon_graph.web.schemas import GraphSchema

SNAPSHOT_FILE = 'graph.json'


def write_static_site(graph: Graph, out_dir: Path) -> None:
    """Write ``index.html``, the UI assets and a JSON snapshot of ``graph``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(Path(str(STATIC)), out_dir / 'static', dirs_exist_ok=True)
    (out_dir / 'index.html').write_text(render_index(snapshot=SNAPSHOT_FILE), encoding='utf-8')
    (out_dir / SNAPSHOT_FILE).write_bytes(
        GraphSchema.model_validate(graph).model_dump_json().encode()
    )
    (out_dir / '.nojekyll').touch()  # serve files as-is on GitHub Pages
