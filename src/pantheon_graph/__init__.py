"""Greek pantheon knowledge graph."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version('pantheon-graph')
except PackageNotFoundError:  # running from a source checkout without installation
    __version__ = '0.0.0'
