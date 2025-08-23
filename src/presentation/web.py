from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from core.config import settings

router = APIRouter(tags=["web"])


@router.get("/", response_class=HTMLResponse)
async def index() -> str:
    api_base = settings.public_api_base or ""
    # Simple one-page Cytoscape visualization with configurable API base
    return f"""
    <!doctype html>
    <html>
      <head>
        <meta charset=\"utf-8\" />
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
        <title>Pantheon Graph</title>
        <style>
          html, body, #cy {{ width: 100%; height: 100%; margin: 0; padding: 0; }}
        </style>
        <script src=\"https://unpkg.com/cytoscape@3.28.1/dist/cytoscape.min.js\"></script>
        <script>
          window.__API_BASE = {api_base!r};
        </script>
      </head>
      <body>
        <div id=\"cy\"></div>
        <script>
          const API = window.__API_BASE || '';
          async function loadGraph() {{
            const res = await fetch(`${{API}}/api/graph/`);
            const data = await res.json();
            const elements = [];
            for (const n of data.nodes) {{
              elements.push({{ data: {{ id: n.id, label: n.label, type: n.type, ...n.props }} }});
            }}
            for (const e of data.edges) {{
              elements.push({{ data: {{ id: e.id, source: e.source, target: e.target, label: e.label, type: e.type, ...e.props }} }});
            }}
            const cy = cytoscape({{
              container: document.getElementById('cy'),
              elements,
              layout: {{ name: 'cose', animate: false }},
              style: [
                {{ selector: 'node', style: {{ 'background-color': '#4f46e5', 'label': 'data(label)', 'color': '#111827', 'text-background-color': '#e0e7ff', 'text-background-opacity': 1, 'text-background-padding': 3, 'font-size': 12 }} }},
                {{ selector: 'edge', style: {{ 'line-color': '#9ca3af', 'target-arrow-color': '#9ca3af', 'target-arrow-shape': 'triangle', 'curve-style': 'bezier', 'width': 2, 'label': 'data(label)', 'font-size': 10, 'color': '#374151', 'text-rotation': 'autorotate' }} }},
              ],
            }});
          }}
          loadGraph();
        </script>
      </body>
    </html>
    """
