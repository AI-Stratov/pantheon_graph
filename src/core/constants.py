"""Application constants to avoid magic numbers and strings."""

from enum import StrEnum


class DatabaseLimits:
    """Database query limits to prevent resource exhaustion."""

    NEO4J_NODE_LIMIT = 2000
    NEO4J_EDGE_LIMIT = 4000
    ARANGO_NODE_LIMIT = 1000
    ARANGO_EDGE_LIMIT = 2000
    WIKIDATA_DEITY_LIMIT = 400
    WIKIDATA_RELATIONSHIP_LIMIT = 4000


class CacheKeys:
    """Redis cache key constants."""

    DEFAULT_GRAPH_KEY = "pantheon:graph"


class WikidataProperties:
    """Wikidata property constants."""

    SPOUSE = "P26"
    FATHER = "P22"
    MOTHER = "P25"
    SIBLING = "P3373"
    INSTANCE_OF = "P31"

    # Q-IDs
    GREEK_DEITY = "Q22989102"


class WikidataEndpoints:
    """Wikidata service endpoints."""

    DEFAULT_SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
    DEFAULT_USER_AGENT = "PantheonGraph/0.1 (+https://example.org)"


class HttpDefaults:
    """HTTP client defaults."""

    DEFAULT_TIMEOUT_SECONDS = 30.0


class RelationshipTypes(StrEnum):
    """Standardized relationship types for graph edges."""

    SPOUSE = "spouse"
    FATHER = "father"
    MOTHER = "mother"
    PARENT = "parent"
    SIBLING = "sibling"


class NodeTypes(StrEnum):
    """Standardized node types for graph nodes."""

    GOD = "god"
    GODDESS = "goddess"
    DEITY = "deity"


class ApiStatusEnum(StrEnum):
    """API status values for consistent status handling across the application."""

    OK = "ok"
    ERROR = "error"
    REFRESHED = "refreshed"

