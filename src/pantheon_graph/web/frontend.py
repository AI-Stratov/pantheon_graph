"""Serving the single-page UI built from ``frontend/`` into ``web/dist``."""

import json
from functools import cache
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse

from pantheon_graph.config import Settings

DIST = Path(__file__).parent / 'dist'
_PLACEHOLDER = '/*%CONFIG%*/{}'
_NOT_BUILT = (
    '<!doctype html><title>Pantheon Graph</title><p>The UI is not built yet. '
    'Run <code>npm ci && npm run build</code> in <code>frontend/</code>.</p>'
)

router = APIRouter(include_in_schema=False)


class FrontendNotBuiltError(FileNotFoundError):
    def __init__(self, dist: Path) -> None:
        super().__init__(f'{dist / "index.html"} is missing: run `npm run build` in frontend/')


@cache
def render_index(dist: Path, *, api_base: str = '', snapshot: str | None = None) -> str:
    """The built ``index.html`` with the runtime config inlined.

    ``snapshot`` points the UI at a static graph JSON file instead of the API,
    which is how the backend-free demo works.
    """
    page = dist / 'index.html'
    if not page.is_file():
        raise FrontendNotBuiltError(dist)
    config = {'apiBase': api_base.rstrip('/'), 'snapshot': snapshot}
    # JSON is a valid JS literal; escaping "</" keeps it inside the <script> tag
    literal = json.dumps(config).replace('</', r'<\/')
    return page.read_text(encoding='utf-8').replace(_PLACEHOLDER, literal)


def _settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def _dist(request: Request) -> Path:
    dist: Path = request.app.state.dist
    return dist


@router.get('/', response_class=HTMLResponse)
async def index(
    settings: Annotated[Settings, Depends(_settings)], dist: Annotated[Path, Depends(_dist)]
) -> HTMLResponse:
    try:
        return HTMLResponse(render_index(dist, api_base=settings.public_api_base))
    except FrontendNotBuiltError:
        return HTMLResponse(_NOT_BUILT, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
