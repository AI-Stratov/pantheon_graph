import cytoscape from 'https://cdn.jsdelivr.net/npm/cytoscape@3.33.1/dist/cytoscape.esm.min.mjs';

import { api } from './api.js';
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
  breadthfirst: { name: 'breadthfirst', directed: true, spacingFactor: 1.1 },
  concentric: { name: 'concentric', minNodeSpacing: 24, concentric: (n) => n.degree(), levelWidth: () => 2 },
  circle: { name: 'circle' },
};

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

  constructor() {
    this.#bindGraphEvents();
    this.#bindControls();
  }

  async load({ refresh = false } = {}) {
    this.#status(refresh ? 'Refreshing data sources…' : 'Loading graph…');
    try {
      if (refresh) await api.refresh();
      this.#render(await api.graph());
      this.#status(this.#graph.nodes.length ? '' : 'The graph is empty: enable at least one source');
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
    this.#renderSearchOptions();
    this.#clearSelection();
  }

  #layout() {
    const name = $('#layout').value;
    const options = { ...LAYOUTS[name], padding: 40 };
    if (name === 'breadthfirst') {
      const roots = this.#cy.nodes().filter((n) => n.incomers('edge[kind = "parent"]').empty());
      if (roots.nonempty()) options.roots = roots;
    }
    this.#cy.layout(options).run();
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

    const { nodes, edges } = this.#graph;
    $('#summary').textContent = `${nodes.length} nodes · ${edges.length} relationships`;
  }

  #applyFilters() {
    this.#cy.batch(() => {
      this.#cy.edges().forEach((edge) => {
        edge.toggleClass('hidden', this.#hiddenKinds.has(edge.data('kind')));
      });
    });
  }

  // ----- selection -----

  #select(id, { focus = true } = {}) {
    const node = this.#cy.getElementById(id);
    if (node.empty()) return;

    this.#clearSelection();
    node.select();
    const neighbourhood = node.closedNeighborhood().not('.hidden');
    this.#cy.elements().not(neighbourhood).addClass('faded');
    neighbourhood.edges().addClass('labelled');

    if (focus) {
      // Fit the neighbourhood but never zoom in further than a comfortable reading level
      const zoom = Math.min(this.#cy.getFitViewport(neighbourhood, 80).zoom, 1.3);
      this.#cy.animate({ zoom, center: { eles: neighbourhood }, duration: 350 });
    }
    this.#renderDetails(node);
  }

  #clearSelection() {
    this.#cy.elements().unselect().removeClass('faded labelled');
    $('#details').hidden = true;
  }

  #renderDetails(node) {
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
        h(
          'ul',
          { className: 'chips' },
          ...items.sort(byLabel).map((item) => {
            const button = h('button', { type: 'button', textContent: item.label });
            button.addEventListener('click', () => this.#select(item.id));
            return h('li', {}, button);
          }),
        ),
      ]),
    );
    $('#details').hidden = false;
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

  // ----- search -----

  #renderSearchOptions() {
    $('#search-options').replaceChildren(
      ...this.#graph.nodes.toSorted(byLabel).map((node) => h('option', { value: node.label })),
    );
  }

  #search(query) {
    const needle = query.trim().toLowerCase();
    if (!needle) return;
    const nodes = this.#graph.nodes;
    const match =
      nodes.find((n) => n.label.toLowerCase() === needle) ??
      nodes.find((n) => n.label.toLowerCase().startsWith(needle)) ??
      nodes.find((n) => n.label.toLowerCase().includes(needle));
    if (match) {
      this.#status('');
      this.#select(match.id);
    } else {
      this.#status(`Nothing found for “${query.trim()}”`);
      setTimeout(() => this.#status(''), 2000);
    }
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
      if (cy.$('node:selected').empty()) event.target.removeClass('labelled');
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
    document.addEventListener('keydown', (event) => {
      if (event.key === '/' && document.activeElement !== $('#search')) {
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
