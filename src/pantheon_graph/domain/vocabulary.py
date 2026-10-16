from enum import StrEnum


class NodeKind(StrEnum):
    """What a figure is; gender is a separate ``gender`` property."""

    PRIMORDIAL = 'primordial'
    TITAN = 'titan'
    OLYMPIAN = 'olympian'
    DEITY = 'deity'
    HERO = 'hero'
    MORTAL = 'mortal'


class Gender(StrEnum):
    MALE = 'male'
    FEMALE = 'female'


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
