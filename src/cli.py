import uvicorn

from core.config import settings


def main() -> None:
    uvicorn.run(
        "presentation.app:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        factory=False,
    )


if __name__ == "__main__":
    # Allow running as a module: `python -m cli` or `uv run -m cli`
    main()
