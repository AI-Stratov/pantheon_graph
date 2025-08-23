# Pantheon Graph

Visualize the Greek pantheon by merging multiple graph adapters into one Cytoscape view.

Live demo:
- URL: https://your-demo-url.example (replace with real link)
- Screenshot: docs/screenshot.png (add an image file)

Highlights:
- Clean DDD: domain / application / infrastructure / presentation
- Multi-adapter: Wikidata (SPARQL), Neo4j, ArangoDB, in-memory
- Caching: Redis or in-memory
- DI: dishka; Background tasks: taskiq
- One-page UI with Cytoscape

Quick start (view):
- Open the live demo above. That’s it.

Quick start (self-host minimal):
- Requirements: Python 3.13+, Redis (optional)
- Setup: uv sync; pre-commit install (optional)
- Run (pick one):
  - uv run src/cli.py
  - uv run -m cli  (ensure PYTHONPATH includes ./src or mark src as Sources Root in your IDE)
  - uv run uvicorn presentation.app:app --host 127.0.0.1 --port 8080  (ensure PYTHONPATH includes ./src)
- Open http://127.0.0.1:8080/

PyCharm run tips:
- Option A (Python configuration): select interpreter at .venv, Script path = src/cli.py, Working directory = project root.
- Option B (Module name): Module name = cli, enable “Add content roots to PYTHONPATH” or mark src as Sources Root.
- Option C (External Tool): Program = uv, Arguments = run $ProjectFileDir$/src/cli.py, Working directory = $ProjectFileDir$.

API:
- GET /health
- GET /api/graph?refresh=false
- GET /api/relationships?source=&target=&type=&label=
- POST /api/graph/refresh

Adapters:
- Wikidata: SPARQL endpoint. Be a good citizen: set a proper User-Agent.
- Neo4j and ArangoDB: read-only snapshots, simple generic queries.


Background worker (optional):
- Requires Redis broker: PANTHEON_REDIS_DSN
- Run: uv run taskiq worker infrastructure.tasks.worker:broker -q
