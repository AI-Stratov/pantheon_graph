class NodeNotFoundError(LookupError):
    """A requested node does not exist in the graph."""

    def __init__(self, node_id: str) -> None:
        super().__init__(f'Node {node_id!r} not found')
        self.node_id = node_id
