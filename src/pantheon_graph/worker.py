"""Background refresh of the shared graph cache.

    taskiq worker pantheon_graph.worker:broker       # executes tasks
    taskiq scheduler pantheon_graph.worker:scheduler # enqueues the periodic refresh

Requires ``PANTHEON_REDIS_URL``: Redis is both the broker and the cache the
web instances read from.
"""

import logging

from dishka.integrations.taskiq import FromDishka, TaskiqProvider, inject, setup_dishka
from taskiq import TaskiqEvents, TaskiqScheduler, TaskiqState
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_redis import RedisStreamBroker

from pantheon_graph.application.service import GraphService
from pantheon_graph.config import get_settings
from pantheon_graph.ioc import make_container
from pantheon_graph.logs import setup_logging

logger = logging.getLogger(__name__)

settings = get_settings()
broker = RedisStreamBroker(settings.redis_url or 'redis://localhost:6379/0')
scheduler = TaskiqScheduler(broker, sources=[LabelScheduleSource(broker)])
container = make_container(settings, TaskiqProvider())
setup_dishka(container, broker)


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def _startup(_: TaskiqState) -> None:
    setup_logging(settings.log_level)
    if not settings.redis_url:
        logger.warning('PANTHEON_REDIS_URL is not set: refreshed graphs stay inside the worker')


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def _shutdown(_: TaskiqState) -> None:
    await container.close()


@broker.task(task_name='pantheon.refresh_graph', schedule=[{'cron': settings.refresh_cron}])
@inject(patch_module=True)
async def refresh_graph(service: FromDishka[GraphService]) -> dict[str, int]:
    """Rebuild the graph from every source and store it in the cache."""
    graph = await service.refresh()
    return {'nodes': len(graph.nodes), 'edges': len(graph.edges)}
