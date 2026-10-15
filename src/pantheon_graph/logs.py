import logging


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=level,
        format='%(asctime)s %(levelname)-7s %(name)s: %(message)s',
        force=True,
    )
    # Query planner hints from the server are useful in development only
    logging.getLogger('neo4j.notifications').setLevel(logging.WARNING)
