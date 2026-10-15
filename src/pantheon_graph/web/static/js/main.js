import cytoscape from 'https://cdn.jsdelivr.net/npm/cytoscape@3.33.1/dist/cytoscape.esm.min.mjs';

import { api, isSnapshot } from './api.js';
import { familyTreePositions } from './family-tree.js';
import { cssVar, edgeStyle, nodeColor, stylesheet } from './theme.js';

const LAYOUTS = {
  cose: {
    name: 'cose',
    animate: false,
    randomize: true,
    nodeDimensionsIncludeLabels: true,
    nodeRepulsion: () => 400_000,
    idealEdgeLength: () => 70,
    gravity: 60,
  },
  tree: { name: 'preset' },
  concentric: { name: 'concentric', minNodeSpacing: 24, concentric: (n) => n.degree(), levelWidth: () => 2 },
  circle: { name: 'circle' },
};
const DEFAULT_LAYOUT = 'cose';

// Showcase questions for the bundled pantheon; pairs missing from the data are skipped
const EXAMPLES = [
  ['heracles', 'uranus'],
  ['hephaestus', 'hermes'],
  ['persephone', 'apollo'],
  ['dionysus', 'amphitrite'],
];

const $ = (selector) => document.querySelector(selector);

function h(tag, props = {}, ...children) {
  const element = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === 'style') Object.entries(value).forEach(([k, v]) => element.style.setProperty(k, v));
    else element[key] = value;
  }
  element.append(...children);
  return element;
}

const countBy = (items, key) =>
  Object.entries(Object.groupBy(items, (item) => item[key] ?? 'unknown'))
    .map(([value, group]) => [value, group.length])
    .sort((a, b) => b[1] - a[1]);

const byLabel = (a, b) => a.label.localeCompare(b.label);

/** How ``edge`` reads when walking from ``node`` to its other end, e.g. "child of". */
function describeStep(edge, node) {
  const kind = edge.data('kind');
  const label = edge.data('label');
  if (kind === 'parent') {
    if (!edge.source().same(node)) return 'child of';
    return `${label && label !== 'parent' ? label : 'parent'} of`;
  }
  if (kind === 'spouse' || kind === 'sibling') return `${kind} of`;
  return label ?? kind;
}

class PantheonView {
  #cy = cytoscape({
    container: $('#cy'),
    style: stylesheet(),
    wheelSensitivity: 0.2,
    minZoom: 0.05,
    maxZoom: 4,
  });
  #graph = { nodes: [], edges: [] };
  #hiddenKinds = new Set();
  #selection = null; // { node } or { from, to }
  // Read once: rendering rewrites the URL before the selection is restored
  #initialParams = new URLSearchParams(location.search);

  constructor() {
    const layout = this.#initialParams.get('layout');
    if (layout in LAYOUTS) $('#layout').value = layout;
    if (isSnapshot) $('[data-action=refresh]').hidden = true;
    this.#bindGraphEvents();
    this.#bindControls();
  }

  async load({ refresh = false } = {}) {
    this.#status(refresh ? 'Refreshing data sources…' : 'Loading graph…');
    try {
      if (refresh) await api.refresh();
      this.#render(await api.graph());
      this.#status(this.#graph.nodes.length ? '' : 'The graph is empty: enable at least one source');
      this.#restoreFromUrl();
    } catch (error) {
      console.error(error);
      this.#status(`Could not load the graph (${error.message})`, { error: true });
    }
  }

  // ----- rendering -----

  #render(graph) {
    this.#graph = graph;
    const nodes = graph.nodes.map(({ properties, ...node }) => ({
      group: 'nodes',
      data: { ...properties, ...node, color: nodeColor(node.kind) },
    }));
    const edges = graph.edges.map(({ properties, ...edge }) => {
      const { color, line, arrow } = edgeStyle(edge.kind);
      return { group: 'edges', data: { ...properties, ...edge, color, line, arrow } };
    });

    this.#cy.batch(() => {
      this.#cy.elements().remove();
      this.#cy.add([...nodes, ...edges]);
    });
    this.#applyFilters();
    this.#layout();
    this.#renderSidebar();
    this.#renderDeityOptions();
    this.#clearSelection();
  }

  #layout() {
    const name = $('#layout').value;
    const options = { ...LAYOUTS[name], padding: 40 };
    if (name === 'tree') options.positions = familyTreePositions(this.#cy);
    this.#cy.layout(options).run();
    this.#syncUrl();
  }

  #renderSidebar() {
    $('#edge-filters').replaceChildren(
      ...countBy(this.#graph.edges, 'kind').map(([kind, count]) => {
        const { color, line } = edgeStyle(kind);
        const checkbox = h('input', { type: 'checkbox', value: kind, checked: !this.#hiddenKinds.has(kind) });
        checkbox.addEventListener('change', () => {
          checkbox.checked ? this.#hiddenKinds.delete(kind) : this.#hiddenKinds.add(kind);
          this.#applyFilters();
        });
        const swatch = h('span', { className: 'line-swatch', style: { '--color': color, '--line': line } });
        return h('label', {}, checkbox, swatch, `${kind} (${count})`);
      }),
    );

    $('#legend').replaceChildren(
      ...countBy(this.#graph.nodes, 'kind').map(([kind, count]) =>
        h('li', {}, h('span', { className: 'swatch', style: { '--color': nodeColor(kind) } }), `${kind} (${count})`),
      ),
    );

    const examples = EXAMPLES.filter(([from, to]) => this.#hasNode(from) && this.#hasNode(to));
    $('#examples').replaceChildren(
      ...examples.map(([from, to]) => {
        const text = `${this.#label(from)} ↔ ${this.#label(to)}`;
        const button = h('button', { type: 'button', textContent: text });
        button.addEventListener('click', () => this.#showPath(from, to));
        return h('li', {}, button);
      }),
    );
    $('.intro').hidden = examples.length === 0;

    const { nodes, edges } = this.#graph;
    $('#summary').textContent = `${nodes.length} nodes · ${edges.length} relationships`;
  }

  #renderDeityOptions() {
    $('#deity-options').replaceChildren(
      ...this.#graph.nodes.toSorted(byLabel).map((node) => h('option', { value: node.label })),
    );
  }

  #applyFilters() {
    this.#cy.batch(() => {
      this.#cy.edges().forEach((edge) => {
        edge.toggleClass('hidden', this.#hiddenKinds.has(edge.data('kind')));
      });
    });
  }

  // ----- selection: one node -----

  #select(id, { focus = true } = {}) {
    const node = this.#cy.getElementById(id);
    if (node.empty()) return;

    this.#clearHighlight();
    this.#selection = { node: id };
    node.select();
    const neighbourhood = node.closedNeighborhood().not('.hidden');
    this.#highlight(neighbourhood);
    neighbourhood.edges().addClass('labelled');

    this.#renderNodeDetails(node);
    if (focus) this.#focus(neighbourhood);
    this.#syncUrl();
  }

  #renderNodeDetails(node) {
    const { id, label, kind, color, ...rest } = node.data();
    $('#details-title').textContent = label;
    const badge = $('#details-kind');
    badge.textContent = kind ?? 'unknown';
    badge.style.setProperty('--color', color);

    $('#details-props').replaceChildren(
      ...Object.entries(rest)
        .filter(([, value]) => value !== null && value !== '' && typeof value !== 'object')
        .flatMap(([key, value]) => {
          const isLink = typeof value === 'string' && /^https?:\/\//.test(value);
          const content = isLink
            ? h('a', { href: value, target: '_blank', rel: 'noopener noreferrer', textContent: 'Open ↗' })
            : String(value);
          return [h('dt', { textContent: key }), h('dd', {}, content)];
        }),
    );

    $('#details-relations').replaceChildren(
      ...[...this.#relations(node)].flatMap(([title, items]) => [
        h('h2', { textContent: `${title} · ${items.length}` }),
        h('ul', { className: 'chips' }, ...items.sort(byLabel).map((item) => h('li', {}, this.#nodeButton(item.id, item.label)))),
      ]),
    );

    $('#path-target').value = '';
    this.#showPanel('node');
  }

  #relations(node) {
    const groups = new Map();
    for (const edge of node.connectedEdges()) {
      const outgoing = edge.source().same(node);
      const other = outgoing ? edge.target() : edge.source();
      const kind = edge.data('kind');
      const title =
        kind === 'parent' ? (outgoing ? 'Children' : 'Parents')
        : kind === 'spouse' ? 'Spouses'
        : kind === 'sibling' ? 'Siblings'
        : edge.data('label') ?? kind;
      const label = kind === 'parent' && !outgoing && edge.data('label') !== 'parent'
        ? `${other.data('label')} (${edge.data('label')})`
        : other.data('label');
      if (!groups.has(title)) groups.set(title, []);
      groups.get(title).push({ id: other.id(), label });
    }
    return groups;
  }

  // ----- selection: path between two nodes -----

  #showPath(from, to) {
    const source = this.#cy.getElementById(from);
    const target = this.#cy.getElementById(to);
    if (source.empty() || target.empty()) return;

    this.#clearHighlight();
    this.#selection = { from, to };
    const { found, path } = this.#cy.elements().not('.hidden').aStar({ root: source, goal: target });

    const names = `${source.data('label')} and ${target.data('label')}`;
    if (!found) {
      $('#path-summary').textContent = `${names} are not connected${this.#hiddenKinds.size ? ' with the current filters' : ''}.`;
      $('#path-steps').replaceChildren();
    } else {
      path.addClass('on-path');
      path.edges().addClass('labelled');
      this.#highlight(path);
      const steps = path.edges().length;
      $('#path-summary').textContent = `${names} are ${steps} step${steps === 1 ? '' : 's'} apart.`;
      $('#path-steps').replaceChildren(...this.#pathSteps(path));
    }
    this.#showPanel('path');
    if (found) this.#focus(path);
    this.#syncUrl();
  }

  #pathSteps(path) {
    const items = [];
    let previous = null;
    for (const element of path) {
      if (element.isEdge()) {
        items.push(h('li', { className: 'relation', textContent: `${describeStep(element, previous)} ↓` }));
      } else {
        const button = this.#nodeButton(element.id(), element.data('label'));
        button.style.setProperty('--color', element.data('color'));
        items.push(h('li', { className: 'node' }, button));
        previous = element;
      }
    }
    return items;
  }

  // ----- shared selection helpers -----

  #nodeButton(id, label) {
    const button = h('button', { type: 'button', textContent: label });
    button.addEventListener('click', () => this.#select(id));
    return button;
  }

  #highlight(elements) {
    this.#cy.elements().not(elements).addClass('faded');
  }

  #focus(elements) {
    this.#cy.resize(); // the details panel may have just changed the canvas width
    // Fit the elements but never zoom in further than a comfortable reading level
    const zoom = Math.min(this.#cy.getFitViewport(elements, 80).zoom, 1.3);
    this.#cy.animate({ zoom, center: { eles: elements }, duration: 350 });
  }

  #clearHighlight() {
    this.#cy.elements().unselect().removeClass('faded labelled on-path');
  }

  #clearSelection() {
    this.#clearHighlight();
    this.#selection = null;
    $('#details').hidden = true;
    this.#cy.resize();
    this.#syncUrl();
  }

  #showPanel(view) {
    $('#node-view').hidden = view !== 'node';
    $('#path-view').hidden = view !== 'path';
    $('#details').hidden = false;
  }

  // ----- search & URL state -----

  #hasNode(id) {
    return this.#cy.getElementById(id).nonempty();
  }

  #label(id) {
    return this.#cy.getElementById(id).data('label');
  }

  #find(query) {
    const needle = query.trim().toLowerCase();
    if (!needle) return null;
    const nodes = this.#graph.nodes;
    return (
      nodes.find((n) => n.label.toLowerCase() === needle || n.id.toLowerCase() === needle) ??
      nodes.find((n) => n.label.toLowerCase().startsWith(needle)) ??
      nodes.find((n) => n.label.toLowerCase().includes(needle)) ??
      null
    );
  }

  #notFound(query) {
    this.#status(`Nothing found for “${query.trim()}”`);
    setTimeout(() => this.#status(''), 2000);
  }

  #search(query) {
    if (!query.trim()) return;
    const match = this.#find(query);
    if (match) this.#select(match.id);
    else this.#notFound(query);
  }

  #syncUrl() {
    const params = new URLSearchParams();
    const layout = $('#layout').value;
    if (layout !== DEFAULT_LAYOUT) params.set('layout', layout);
    if (this.#selection?.node) params.set('node', this.#selection.node);
    if (this.#selection?.from) {
      params.set('from', this.#selection.from);
      params.set('to', this.#selection.to);
    }
    const query = params.size ? `?${params}` : '';
    if (query !== location.search) history.replaceState(null, '', `${location.pathname}${query}`);
  }

  #restoreFromUrl() {
    const params = this.#initialParams;
    if (params.has('from') && params.has('to')) this.#showPath(params.get('from'), params.get('to'));
    else if (params.has('node')) this.#select(params.get('node'));
  }

  // ----- wiring -----

  #bindGraphEvents() {
    const cy = this.#cy;
    cy.on('tap', 'node', (event) => this.#select(event.target.id(), { focus: false }));
    cy.on('tap', (event) => event.target === cy && this.#clearSelection());
    cy.on('dbltap', 'node', (event) =>
      cy.animate({ zoom: Math.min(cy.zoom() * 1.6, cy.maxZoom()), center: { eles: event.target }, duration: 300 }),
    );
    cy.on('mouseover', 'edge', (event) => event.target.addClass('labelled'));
    cy.on('mouseout', 'edge', (event) => {
      if (!this.#selection) event.target.removeClass('labelled');
    });
  }

  #bindControls() {
    const actions = {
      fit: () => this.#cy.animate({ fit: { eles: this.#cy.elements(':visible'), padding: 40 }, duration: 300 }),
      reset: () => {
        $('#search').value = '';
        this.#clearSelection();
        actions.fit();
      },
      refresh: async (button) => {
        button.disabled = true;
        await this.load({ refresh: true });
        button.disabled = false;
      },
      export: () => this.#exportPng(),
      close: () => this.#clearSelection(),
    };
    document.addEventListener('click', (event) => {
      const button = event.target.closest('[data-action]');
      if (button) actions[button.dataset.action]?.(button);
    });

    $('#layout').addEventListener('change', () => this.#layout());
    $('#search-form').addEventListener('submit', (event) => {
      event.preventDefault();
      this.#search($('#search').value);
    });
    $('#search').addEventListener('change', (event) => this.#search(event.target.value));
    $('#path-form').addEventListener('submit', (event) => {
      event.preventDefault();
      const query = $('#path-target').value;
      const target = this.#find(query);
      if (target && this.#selection?.node) this.#showPath(this.#selection.node, target.id);
      else this.#notFound(query);
    });
    document.addEventListener('keydown', (event) => {
      const typing = ['INPUT', 'SELECT'].includes(document.activeElement?.tagName);
      if (event.key === '/' && !typing) {
        event.preventDefault();
        $('#search').focus();
      } else if (event.key === 'Escape') {
        actions.reset();
      }
    });
    matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
      this.#cy.style(stylesheet());
    });
  }

  #exportPng() {
    const href = this.#cy.png({ full: true, scale: 2, bg: cssVar('--bg') });
    h('a', { href, download: 'pantheon-graph.png' }).click();
  }

  #status(message, { error = false } = {}) {
    const status = $('#status');
    status.textContent = message;
    status.classList.toggle('error', error);
  }
}

new PantheonView().load();
