from functools import cached_property

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class Neo4jConfig(BaseModel):
    uri: str
    user: str
    password: str


class ArangoConfig(BaseModel):
    url: str
    db: str
    user: str
    password: str
    graph: str | None = None  # optional Arango Graph name
    vertex_collection: str | None = None  # fallback if graph is not used
    edge_collection: str | None = None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PANTHEON_", env_file=".env", extra="ignore")

    app_name: str = "Pantheon Graph"
    host: str = "127.0.0.1"
    port: int = 8080

    # Frontend → Adapter integration
    public_api_base: str | None = None  # e.g. https://api.example.com
    cors_origins: list[str] = []  # e.g. ["https://example.github.io", "https://demo.example.com"]

    # Adapters toggles
    enable_memory_adapter: bool = True
    enable_neo4j_adapter: bool = False
    enable_arango_adapter: bool = False
    enable_wikidata_adapter: bool = False

    # Neo4j
    neo4j_uri: str | None = None
    neo4j_user: str | None = None
    neo4j_password: str | None = None

    # ArangoDB
    arango_url: str | None = None
    arango_db: str | None = None
    arango_user: str | None = None
    arango_password: str | None = None
    arango_graph: str | None = None
    arango_vertex_collection: str | None = None
    arango_edge_collection: str | None = None

    # Wikidata
    wikidata_endpoint: str = "https://query.wikidata.org/sparql"
    wikidata_user_agent: str = "PantheonGraph/0.1 (+https://example.org)"

    # Infra
    redis_dsn: str | None = None

    @cached_property
    def neo4j(self) -> Neo4jConfig | None:
        if not self.enable_neo4j_adapter:
            return None
        if not (self.neo4j_uri and self.neo4j_user and self.neo4j_password):
            return None
        return Neo4jConfig(uri=self.neo4j_uri, user=self.neo4j_user, password=self.neo4j_password)

    @cached_property
    def arango(self) -> ArangoConfig | None:
        if not self.enable_arango_adapter:
            return None
        if not (self.arango_url and self.arango_db and self.arango_user and self.arango_password):
            return None
        return ArangoConfig(
            url=self.arango_url,
            db=self.arango_db,
            user=self.arango_user,
            password=self.arango_password,
            graph=self.arango_graph,
            vertex_collection=self.arango_vertex_collection,
            edge_collection=self.arango_edge_collection,
        )


settings = Settings()  # evaluate once at import for app-wide usage
