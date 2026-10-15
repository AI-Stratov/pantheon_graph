import logging
from contextlib import AsyncExitStack

from pantheon_graph.application.ports import GraphSource
from pantheon_graph.config import ArangoSettings, Neo4jSettings, Settings, WikidataSettings

logger = logging.getLogger(__name__)


async def open_sources(settings: Settings, stack: AsyncExitStack) -> list[GraphSource]:
    """Create every enabled source; their connections are closed together with ``stack``.

    Drivers are imported lazily so a disabled backend costs nothing at startup.
    """
    sources: list[GraphSource] = []
    if settings.memory.enabled:
        from pantheon_graph.infrastructure.sources.memory import MemorySource

        sources.append(MemorySource.bundled())
    if settings.wikidata.enabled:
        sources.append(await _wikidata(settings.wikidata, stack))
    if settings.neo4j.enabled:
        sources.append(await _neo4j(settings.neo4j, stack))
    if settings.arango.enabled:
        sources.append(await _arango(settings.arango, stack))

    if sources:
        logger.info('Graph sources: %s', ', '.join(source.name for source in sources))
    else:
        logger.warning('No graph sources enabled, the graph will be empty')
    return sources


async def _wikidata(settings: WikidataSettings, stack: AsyncExitStack) -> GraphSource:
    import httpx2 as httpx

    from pantheon_graph.infrastructure.sources.wikidata import WikidataSource

    client = httpx.AsyncClient(
        timeout=settings.http_timeout, headers={'User-Agent': settings.user_agent}
    )
    return WikidataSource(await stack.enter_async_context(client), settings)


async def _neo4j(settings: Neo4jSettings, stack: AsyncExitStack) -> GraphSource:
    from neo4j import AsyncGraphDatabase

    from pantheon_graph.infrastructure.sources.neo4j import Neo4jSource

    auth = (settings.user, settings.password.get_secret_value())
    driver = AsyncGraphDatabase.driver(
        settings.uri,
        auth=auth,
        connection_timeout=settings.connect_timeout,
        max_transaction_retry_time=settings.connect_timeout,
    )
    return Neo4jSource(await stack.enter_async_context(driver), settings)


async def _arango(settings: ArangoSettings, stack: AsyncExitStack) -> GraphSource:
    from arangoasync import ArangoClient
    from arangoasync.auth import Auth

    from pantheon_graph.infrastructure.sources.arango import ArangoSource

    client = await stack.enter_async_context(ArangoClient(hosts=settings.url))
    auth = Auth(username=settings.user, password=settings.password.get_secret_value())
    return ArangoSource(await client.db(settings.database, auth=auth), settings)
