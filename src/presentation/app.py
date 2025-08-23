from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from fastapi.middleware.cors import CORSMiddleware

from dishka.integrations.fastapi import setup_dishka, FastapiProvider
from dishka import make_async_container

from core.config import settings
from infrastructure.di import AppProvider
from presentation.api.graph import router as api_graph_router
from presentation.web import router as web_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await app.state.dishka_container.close()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        default_response_class=ORJSONResponse,
        lifespan=lifespan
    )

    container = make_async_container(AppProvider(), FastapiProvider())
    setup_dishka(container, app)

    # Enable CORS only if origins configured
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Mount API and UI routers
    app.include_router(api_graph_router)
    app.include_router(web_router)

    return app


app = create_app()
