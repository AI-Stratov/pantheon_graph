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
          #controls {{
            position: absolute;
            top: 10px;
            right: 10px;
            z-index: 1000;
            background: rgba(255, 255, 255, 0.9);
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
          }}
          #controls button {{
            margin: 2px;
            padding: 5px 10px;
            border: none;
            border-radius: 3px;
            background: #4f46e5;
            color: white;
            cursor: pointer;
          }}
          #controls button:hover {{
            background: #3730a3;
          }}
        </style>
        <script src=\"https://unpkg.com/cytoscape@3.28.1/dist/cytoscape.min.js\"></script>
        <script>
          window.__API_BASE = {api_base!r};
        </script>
      </head>
      <body>
        <div id=\"controls\">
          <button onclick=\"centerGraph()\">📍 Center</button>
          <button onclick=\"fitGraph()\">🔍 Fit screen</button>
          <button onclick=\"resetZoom()\">↺ Reset</button>
        </div>
        <div id=\"cy\"></div>
        <script>
          const API = window.__API_BASE || '';
          let cy;
          
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
            
            cy = cytoscape({{
              container: document.getElementById('cy'),
              elements,
              layout: {{ name: 'cose', animate: false }},
              
              // Улучшенные настройки взаимодействия
              wheelSensitivity: 0.1,  // Менее чувствительное колесико
              minZoom: 0.1,
              maxZoom: 3,
              
              style: [
                {{ selector: 'node', style: {{ 
                  'background-color': '#4f46e5', 
                  'label': 'data(label)', 
                  'color': '#111827', 
                  'text-background-color': '#e0e7ff', 
                  'text-background-opacity': 1, 
                  'text-background-padding': 3, 
                  'font-size': 12,
                  'width': 30,
                  'height': 30
                }} }},
                {{ selector: 'edge', style: {{ 
                  'line-color': '#9ca3af', 
                  'target-arrow-color': '#9ca3af', 
                  'target-arrow-shape': 'triangle', 
                  'curve-style': 'bezier', 
                  'width': 2, 
                  'label': 'data(label)', 
                  'font-size': 10, 
                  'color': '#374151', 
                  'text-rotation': 'autorotate' 
                }} }},
              ],
            }});
            
            // Центрируем граф после загрузки
            cy.fit(50);
            cy.center();
            
            // Добавляем плавное масштабирование при двойном клике
            cy.on('doubleTap', 'node', function(evt) {{
              cy.animate({{
                zoom: cy.zoom() * 1.5,
                center: {{
                  eles: evt.target
                }}
              }}, {{
                duration: 500
              }});
            }});
          }}
          
          // Функции управления
          function centerGraph() {{
            if (cy) {{
              cy.animate({{
                center: {{ eles: cy.elements() }}
              }}, {{ duration: 300 }});
            }}
          }}
          
          function fitGraph() {{
            if (cy) {{
              cy.animate({{
                fit: {{
                  eles: cy.elements(),
                  padding: 50
                }}
              }}, {{ duration: 300 }});
            }}
          }}
          loadGraph();
        </script>
      </body>
    </html>
    """
