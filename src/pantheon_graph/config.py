"""Settings read from ``PANTHEON_*`` environment variables (or a ``.env`` file).

Nested sections use a double underscore, e.g. ``PANTHEON_NEO4J__ENABLED=true``.
"""

import json
from functools import lru_cache
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

type LogLevel = Literal['DEBUG', 'INFO', 'WARNING', 'ERROR']


class MemorySettings(BaseModel):
    enabled: bool = True


class WikidataSettings(BaseModel):
    enabled: bool = False
    endpoint: str = 'https://query.wikidata.org/sparql'
    # Wikimedia asks every client to identify itself with a contact URL or email
    user_agent: str = 'PantheonGraph/1.0 (https://github.com/AI-Stratov/pantheon_graph)'
    language: str = 'en'
    http_timeout: float = Field(default=30.0, gt=0)
    node_limit: int = Field(default=400, gt=0)
    edge_limit: int = Field(default=4000, gt=0)


class Neo4jSettings(BaseModel):
    enabled: bool = False
    uri: str = 'neo4j://localhost:7687'
    user: str = 'neo4j'
    password: SecretStr = SecretStr('')
    database: str | None = None
    # Bounds the driver's own connect/retry loop so an outage fails fast
    connect_timeout: float = Field(default=5.0, gt=0)
    node_limit: int = Field(default=2000, gt=0)
    edge_limit: int = Field(default=4000, gt=0)


class ArangoSettings(BaseModel):
    enabled: bool = False
    url: str = 'http://localhost:8529'
    database: str = '_system'
    user: str = 'root'
    password: SecretStr = SecretStr('')
    graph: str | None = 'pantheon'
    vertex_collection: str | None = None
    edge_collection: str | None = None
    node_limit: int = Field(default=1000, gt=0)
    edge_limit: int = Field(default=2000, gt=0)

    @model_validator(mode='after')
    def _require_collections(self) -> Self:
        explicit = self.vertex_collection and self.edge_collection
        if self.enabled and not (explicit or self.graph):
            msg = 'set either graph or both vertex_collection and edge_collection'
            raise ValueError(msg)
        return self


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix='PANTHEON_',
        env_nested_delimiter='__',
        env_file='.env',
        extra='ignore',
    )

    title: str = 'Pantheon Graph'
    host: str = '127.0.0.1'
    port: int = Field(default=8080, ge=1, le=65535)
    log_level: LogLevel = 'INFO'

    # Base URL of the API when the UI is served from another origin
    public_api_base: str = ''
    # JSON list or comma separated origins allowed to call the API from a browser
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)

    memory: MemorySettings = MemorySettings()
    wikidata: WikidataSettings = WikidataSettings()
    neo4j: Neo4jSettings = Neo4jSettings()
    arango: ArangoSettings = ArangoSettings()

    source_timeout: float = Field(default=30.0, gt=0)
    # Redis enables the shared cache and the background worker
    redis_url: str | None = None
    cache_ttl: int | None = Field(default=3600, ge=1, description='seconds; 0 disables expiry')
    refresh_cron: str = '*/30 * * * *'

    @field_validator('log_level', mode='before')
    @classmethod
    def _upper_log_level(cls, value: Any) -> Any:
        return value.upper() if isinstance(value, str) else value

    @field_validator('cors_origins', mode='before')
    @classmethod
    def _split_origins(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value
        if value.lstrip().startswith('['):
            return json.loads(value)
        return [origin.strip() for origin in value.split(',') if origin.strip()]

    @field_validator('cache_ttl', mode='before')
    @classmethod
    def _zero_ttl_means_forever(cls, value: Any) -> Any:
        return None if value in (0, '0', '') else value


@lru_cache
def get_settings() -> Settings:
    return Settings()
