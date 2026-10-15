from enum import StrEnum


class NodeKind(StrEnum):
    PRIMORDIAL = 'primordial'
    TITAN = 'titan'
    GOD = 'god'
    GODDESS = 'goddess'
    DEITY = 'deity'
    MORTAL = 'mortal'
    HERO = 'hero'


class Relation(StrEnum):
    """Edge kinds shared by every source.

    ``PARENT`` edges always point from parent to child; ``SPOUSE`` and
    ``SIBLING`` are symmetric and stored once per pair.
    """

    PARENT = 'parent'
    SPOUSE = 'spouse'
    SIBLING = 'sibling'

    @property
    def is_symmetric(self) -> bool:
        return self is not Relation.PARENT
