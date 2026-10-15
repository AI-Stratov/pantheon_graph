"""Command line entry point: serve the app or seed a database."""

import argparse
import asyncio
import sys
from collections.abc import Sequence

from pantheon_graph.config import get_settings
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

    args = parser.parse_args(argv)
    match args.command:
        case 'seed':
            _seed(args.target)
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


if __name__ == '__main__':
    main()
