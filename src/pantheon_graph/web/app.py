from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from dishka.integrations.fastapi import FastapiProvider, setup_dishka
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from pantheon_graph import __version__
from pantheon_graph.application.aggregator import AllSourcesFailedError
from pantheon_graph.config import Settings, get_settings
from pantheon_graph.domain import NodeNotFoundError, PathNotFoundError
from pantheon_graph.ioc import make_container
from pantheon_graph.logs import setup_logging
from pantheon_graph.web import api, frontend


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await app.state.dishka_container.close()


async def _not_found(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse({'detail': str(exc)}, status_code=status.HTTP_404_NOT_FOUND)


async def _sources_failed(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse({'detail': str(exc)}, status_code=status.HTTP_503_SERVICE_UNAVAILABLE)


def create_app(settings: Settings | None = None, *, dist: Path = frontend.DIST) -> FastAPI:
    settings = settings or get_settings()
    setup_logging(settings.log_level)

    app = FastAPI(
        title=settings.title,
        version=__version__,
        summary='Greek pantheon merged from several graph sources',
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.dist = dist
    setup_dishka(make_container(settings, FastapiProvider()), app)

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_methods=['GET', 'POST'],
            allow_headers=['*'],
        )

    app.add_exception_handler(NodeNotFoundError, _not_found)
    app.add_exception_handler(PathNotFoundError, _not_found)
    app.add_exception_handler(AllSourcesFailedError, _sources_failed)

    app.include_router(api.health_router)
    app.include_router(api.graph_router)
    app.include_router(frontend.router)
    # Built assets (JS, CSS, fonts, favicon); registered last so API routes win
    app.mount('/', StaticFiles(directory=dist, check_dir=False), name='ui')
    return app
