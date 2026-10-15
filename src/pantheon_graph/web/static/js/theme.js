const NODE_COLORS = {
  primordial: '#7c3aed',
  titan: '#b45309',
  god: '#2563eb',
  goddess: '#db2777',
  deity: '#0d9488',
  mortal: '#64748b',
  hero: '#16a34a',
};
const FALLBACK_COLORS = ['#0891b2', '#ca8a04', '#9333ea', '#e11d48', '#65a30d', '#475569'];

const EDGE_STYLES = {
  parent: { color: '#94a3b8', line: 'solid', arrow: 'triangle' },
  spouse: { color: '#f43f5e', line: 'dashed', arrow: 'none' },
  sibling: { color: '#22c55e', line: 'dotted', arrow: 'none' },
};
const DEFAULT_EDGE_STYLE = { color: '#a8a29e', line: 'solid', arrow: 'triangle' };

function hashColor(value) {
  let hash = 0;
  for (const char of value) hash = (Math.imul(hash, 31) + char.charCodeAt(0)) | 0;
  return FALLBACK_COLORS[Math.abs(hash) % FALLBACK_COLORS.length];
}

export const nodeColor = (kind) => NODE_COLORS[kind] ?? hashColor(kind ?? 'unknown');
export const edgeStyle = (kind) => EDGE_STYLES[kind] ?? DEFAULT_EDGE_STYLE;

/** Resolve a CSS custom property to a concrete rgb() colour (light-dark() included). */
export function cssVar(name) {
  const probe = document.createElement('span');
  probe.style.color = `var(${name})`;
  document.body.append(probe);
  const color = getComputedStyle(probe).color;
  probe.remove();
  return color;
}

const nodeSize = (node) => 18 + Math.min(node.degree(), 12) * 2;

export function stylesheet() {
  const text = cssVar('--text');
  return [
    {
      selector: 'node',
      style: {
        'background-color': 'data(color)',
        label: 'data(label)',
        color: text,
        'font-size': 11,
        'text-valign': 'bottom',
        'text-margin-y': 4,
        'text-background-color': cssVar('--panel'),
        'text-background-opacity': 0.8,
        'text-background-padding': 2,
        'text-background-shape': 'roundrectangle',
        width: nodeSize,
        height: nodeSize,
        'transition-property': 'opacity',
        'transition-duration': 150,
      },
    },
    {
      selector: 'edge',
      style: {
        width: 1.6,
        'line-color': 'data(color)',
        'line-style': 'data(line)',
        'target-arrow-color': 'data(color)',
        'target-arrow-shape': 'data(arrow)',
        'arrow-scale': 0.9,
        'curve-style': 'bezier',
        'transition-property': 'opacity',
        'transition-duration': 150,
      },
    },
    {
      selector: 'edge.labelled',
      style: { label: 'data(label)', color: text, 'font-size': 9, 'text-rotation': 'autorotate' },
    },
    { selector: 'node:selected', style: { 'border-width': 3, 'border-color': cssVar('--accent') } },
    { selector: '.faded', style: { opacity: 0.12 } },
    {
      selector: 'node.on-path',
      style: { 'border-width': 4, 'border-color': cssVar('--accent'), 'z-index': 10 },
    },
    {
      selector: 'edge.on-path',
      style: { width: 4, 'line-color': cssVar('--accent'), 'target-arrow-color': cssVar('--accent'), 'z-index': 10 },
    },
    { selector: '.hidden', style: { display: 'none' } },
  ];
}
