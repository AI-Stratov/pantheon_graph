import json
from functools import cache
from importlib.resources import files
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from pantheon_graph.config import Settings

STATIC = files(__package__) / 'static'
_PLACEHOLDER = '"%API_BASE%"'

router = APIRouter(include_in_schema=False)


def _settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


@cache
def render_index(api_base: str) -> str:
    template = (STATIC / 'index.html').read_text(encoding='utf-8')
    # A JSON string is a valid JS literal; escaping "</" keeps it inside the <script> tag
    literal = json.dumps(api_base.rstrip('/')).replace('</', r'<\/')
    return template.replace(_PLACEHOLDER, literal)


@router.get('/', response_class=HTMLResponse)
async def index(settings: Annotated[Settings, Depends(_settings)]) -> str:
    return render_index(settings.public_api_base)
