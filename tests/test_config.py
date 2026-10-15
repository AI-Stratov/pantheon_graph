import pytest
from pydantic import ValidationError

from pantheon_graph.config import Settings


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch, settings: Settings) -> pytest.MonkeyPatch:
    return monkeypatch  # the settings fixture already cleared PANTHEON_* variables


def load() -> Settings:
    return Settings(_env_file=None)


@pytest.mark.parametrize(
    ('raw', 'expected'),
    [
        ('https://a.example, https://b.example', ['https://a.example', 'https://b.example']),
        ('["https://a.example"]', ['https://a.example']),
        ('', []),
    ],
)
def test_cors_origins_accept_csv_and_json(
    env: pytest.MonkeyPatch, raw: str, expected: list[str]
) -> None:
    env.setenv('PANTHEON_CORS_ORIGINS', raw)

    assert load().cors_origins == expected


def test_nested_sections(env: pytest.MonkeyPatch) -> None:
    env.setenv('PANTHEON_NEO4J__ENABLED', 'true')
    env.setenv('PANTHEON_NEO4J__PASSWORD', 'secret')
    env.setenv('PANTHEON_LOG_LEVEL', 'debug')

    settings = load()

    assert settings.neo4j.enabled
    assert settings.neo4j.password.get_secret_value() == 'secret'
    assert 'secret' not in repr(settings)
    assert settings.log_level == 'DEBUG'


def test_zero_ttl_disables_expiry(env: pytest.MonkeyPatch) -> None:
    env.setenv('PANTHEON_CACHE_TTL', '0')

    assert load().cache_ttl is None


def test_arango_requires_graph_or_collections(env: pytest.MonkeyPatch) -> None:
    env.setenv('PANTHEON_ARANGO__ENABLED', 'true')
    env.setenv('PANTHEON_ARANGO__GRAPH', '')

    with pytest.raises(ValidationError, match='vertex_collection'):
        load()
