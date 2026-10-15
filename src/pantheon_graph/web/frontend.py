import json
from functools import cache
from importlib.resources import files
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from pantheon_graph.config import Settings

STATIC = files(__package__) / 'static'
TEMPLATE = files(__package__) / 'index.html'
_PLACEHOLDER = '/*%CONFIG%*/{}'

router = APIRouter(include_in_schema=False)


@cache
def render_index(*, api_base: str = '', snapshot: str | None = None) -> str:
    """The UI page with its runtime config inlined.

    ``snapshot`` points the UI at a static graph JSON file instead of the API,
    which is how the backend-free demo build works.
    """
    template = TEMPLATE.read_text(encoding='utf-8')
    config = {'apiBase': api_base.rstrip('/'), 'snapshot': snapshot}
    # JSON is a valid JS literal; escaping "</" keeps it inside the <script> tag
    return template.replace(_PLACEHOLDER, json.dumps(config).replace('</', r'<\/'))


def _settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


@router.get('/', response_class=HTMLResponse)
async def index(settings: Annotated[Settings, Depends(_settings)]) -> str:
    return render_index(api_base=settings.public_api_base)
