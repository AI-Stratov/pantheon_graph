"""Command line entry point: serve the app, seed a database or export a static demo."""

import argparse
import asyncio
import sys
from collections.abc import Sequence
from pathlib import Path

from pantheon_graph.config import Settings, get_settings
from pantheon_graph.domain import Graph
from pantheon_graph.logs import setup_logging


def main(argv: Sequence[str] | None = None) -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(prog='pantheon-graph', description=__doc__)
    commands = parser.add_subparsers(dest='command')

    serve = commands.add_parser('serve', help='run the web server (default)')
    serve.add_argument('--host', default=settings.host)
    serve.add_argument('--port', type=int, default=settings.port)
    serve.add_argument('--reload', action='store_true', help='restart on code changes')

    seed = commands.add_parser('seed', help='load the bundled pantheon into a database')
    seed.add_argument('target', choices=['neo4j', 'arango'])

    export = commands.add_parser(
        'export', help='build a static, backend-free copy of the UI (e.g. for GitHub Pages)'
    )
    export.add_argument('out_dir', type=Path, nargs='?', default=Path('site'))

    args = parser.parse_args(argv)
    match args.command:
        case 'seed':
            _seed(args.target)
        case 'export':
            _export(args.out_dir)
        case 'serve':
            _serve(args.host, args.port, reload=args.reload)
        case _:
            _serve(settings.host, settings.port, reload=False)


def _serve(host: str, port: int, *, reload: bool) -> None:
    import uvicorn

    uvicorn.run(
        'pantheon_graph.web.app:create_app',
        factory=True,
        host=host,
        port=port,
        reload=reload,
        proxy_headers=True,
        log_config=None,  # the app configures logging itself
    )


def _seed(target: str) -> None:
    from pantheon_graph.infrastructure.seed import seed_arango, seed_neo4j
    from pantheon_graph.infrastructure.sources.memory import MemorySource

    settings = get_settings()
    setup_logging(settings.log_level)
    graph = asyncio.run(MemorySource.bundled().fetch())
    seed = (
        seed_neo4j(graph, settings.neo4j)
        if target == 'neo4j'
        else seed_arango(graph, settings.arango)
    )
    try:
        asyncio.run(seed)
    except Exception as exc:
        sys.exit(f'Seeding {target} failed: {exc}')


def _export(out_dir: Path) -> None:
    from pantheon_graph.web.snapshot import write_static_site

    settings = get_settings()
    setup_logging(settings.log_level)
    graph = asyncio.run(_snapshot(settings))
    write_static_site(graph, out_dir)
    print(f'Static site with {len(graph.nodes)} nodes written to {out_dir}/')


async def _snapshot(settings: Settings) -> Graph:
    """Build the graph exactly as the server would, from every enabled source."""
    from pantheon_graph.application.service import GraphService
    from pantheon_graph.ioc import make_container

    container = make_container(settings)
    try:
        service = await container.get(GraphService)
        return await service.refresh()
    finally:
        await container.close()


if __name__ == '__main__':
    main()
