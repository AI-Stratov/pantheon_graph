<script lang="ts">
  import cytoscape, { type Core, type EdgeSingular, type ElementDefinition, type StylesheetJson } from 'cytoscape';
  import fcose from 'cytoscape-fcose';
  import { onMount } from 'svelte';

  import { familyTree, type Point } from '../lib/familyTree';
  import type { Pantheon, Path } from '../lib/graph';
  import { describeStep, roleLabel } from '../lib/kinship';
  import { withSeed } from '../lib/random';
  import type { AppState, Layout } from '../lib/state.svelte';
  import type { Insets } from '../lib/types';
  import { kindStyle, medallionSvg, RELATIONS, RELATION_FALLBACK } from '../lib/theme';

  interface Props {
    pantheon: Pantheon;
    app: AppState;
    path: Path | null;
    insets: Insets;
    onselect: (id: string) => void;
    onclear: () => void;
  }

  let { pantheon, app, path, insets, onselect, onclear }: Props = $props();

  cytoscape.use(fcose);

  const LABEL_FONT = '"Cormorant Garamond Variable", Georgia, serif';
  const UI_FONT = '"Inter Variable", system-ui, sans-serif';
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  // Beyond this many relatives the role captions would cover each other
  const MAX_PINNED_CAPTIONS = 9;

  let container: HTMLDivElement;
  let cy = $state.raw<Core | null>(null);
  const layouts = new Map<Layout, Record<string, Point>>();

  function elements(): ElementDefinition[] {
    const nodes = pantheon.nodes.map((node) => ({
      group: 'nodes' as const,
      data: {
        id: node.id,
        label: node.label,
        tone: kindStyle(node.kind).color,
        image: medallionSvg(node),
        size: kindStyle(node.kind).size + Math.min(pantheon.degree(node.id), 14) * 0.9,
      },
    }));
    const edges = pantheon.edges.map((edge) => {
      const relation = RELATIONS[edge.kind] ?? RELATION_FALLBACK;
      return {
        group: 'edges' as const,
        data: { id: edge.id, source: edge.source, target: edge.target, kind: edge.kind, tone: relation.color, dash: relation.dash, caption: '' },
      };
    });
    return [...nodes, ...edges];
  }

  const INK = '#29241e';
  const BG = '#f2ede4';
  const SKY = '#2f5d8a';

  const style: StylesheetJson = [
    {
      selector: 'node',
      style: {
        width: 'data(size)',
        height: 'data(size)',
        'background-image': 'data(image)',
        'background-fit': 'cover',
        'background-opacity': 0,
        label: 'data(label)',
        color: INK,
        'font-family': LABEL_FONT,
        'font-size': 15,
        'font-weight': 700,
        'text-valign': 'bottom',
        'text-margin-y': 5,
        // Keeps names legible where they cross a line
        'text-outline-color': BG,
        'text-outline-width': 2.5,
        'min-zoomed-font-size': 8,
        'transition-property': 'opacity',
        'transition-duration': 200,
      },
    },
    {
      selector: 'edge',
      style: {
        width: 1.3,
        'line-color': 'data(tone)',
        'line-opacity': 0.55,
        'line-style': 'data(dash)' as never,
        'line-dash-pattern': [6, 4],
        'curve-style': 'straight',
        'transition-property': 'opacity',
        'transition-duration': 200,
      },
    },
    {
      selector: 'edge[kind = "parent"]',
      style: { 'mid-target-arrow-shape': 'triangle', 'mid-target-arrow-color': 'data(tone)', 'arrow-scale': 0.7 },
    },
    {
      selector: 'edge.tree[kind = "parent"]',
      style: { 'curve-style': 'taxi', 'taxi-direction': 'downward', 'taxi-turn': '45%', 'mid-target-arrow-shape': 'none' },
    },
    {
      selector: 'edge.tree[kind != "parent"]',
      style: { 'curve-style': 'unbundled-bezier', 'control-point-distances': [-34], 'control-point-weights': [0.5] },
    },
    // Cytoscape's built-in press feedback is a dark square; keep it round and light
    { selector: 'core', style: { 'active-bg-opacity': 0 } as cytoscape.Css.Core },
    {
      selector: 'node:active',
      style: { 'overlay-color': SKY, 'overlay-opacity': 0.14, 'overlay-padding': 6, 'overlay-shape': 'ellipse' },
    },
    { selector: 'edge:active', style: { 'overlay-opacity': 0 } },
    { selector: '.hidden', style: { display: 'none' } },
    { selector: 'node.hover', style: { 'border-width': 2, 'border-color': INK } },
    { selector: 'node.dim', style: { opacity: 0.22 } },
    { selector: 'edge.dim', style: { opacity: 0.1 } },
    { selector: 'node.focus', style: { 'border-width': 3, 'border-color': SKY, 'font-size': 17 } },
    {
      selector: 'edge.captioned',
      style: {
        label: 'data(caption)',
        color: INK,
        'font-family': UI_FONT,
        'font-size': 10.5,
        'font-weight': 600,
        'text-rotation': 'none',
        'text-background-color': '#fbf9f4',
        'text-background-opacity': 1,
        'text-background-padding': '4px',
        'text-background-shape': 'roundrectangle',
        'text-border-color': '#c8bba5',
        'text-border-opacity': 1,
        'text-border-width': 1,
        'line-opacity': 0.9,
        width: 1.8,
        'z-index': 10,
      },
    },
    { selector: 'node.onpath', style: { 'border-width': 3, 'border-color': SKY, 'font-size': 16 } },
    {
      selector: 'edge.onpath',
      style: {
        width: 3,
        'line-color': SKY,
        'line-opacity': 1,
        'mid-target-arrow-color': SKY,
        color: '#fff',
        'text-background-color': SKY,
        'text-border-width': 0,
        'z-index': 20,
      },
    },
  ];

  /** Constellation positions: force-directed, but seeded so every visit looks the same. */
  function constellation(core: Core): Record<string, Point> {
    withSeed(20240917, () =>
      core
        .layout({
          name: 'fcose',
          quality: 'proof',
          randomize: true,
          animate: false,
          nodeDimensionsIncludeLabels: true,
          packComponents: true,
          nodeRepulsion: () => 16000,
          idealEdgeLength: (edge: EdgeSingular) => (edge.data('kind') === 'parent' ? 95 : 70),
          edgeElasticity: () => 0.35,
          gravity: 0.3,
          numIter: 4000,
        } as cytoscape.LayoutOptions)
        .run(),
    );
    return Object.fromEntries(core.nodes().map((node) => [node.id(), { ...node.position() }]));
  }

  function positionsFor(core: Core, layout: Layout): Record<string, Point> {
    let positions = layouts.get(layout);
    if (!positions) {
      positions = layout === 'tree' ? Object.fromEntries(familyTree(pantheon)) : constellation(core);
      layouts.set(layout, positions);
    }
    return positions;
  }

  /**
   * Fit ``eles`` into the part of the canvas not covered by floating panels.
   * Below ``minZoom`` the view centres on ``anchor`` instead, so a sprawling
   * selection stays readable and the rest is a pan away.
   */
  function frame(
    core: Core,
    eles: cytoscape.Collection,
    { animate = true, minZoom = core.minZoom(), anchor }: { animate?: boolean; minZoom?: number; anchor?: cytoscape.Collection } = {},
  ) {
    if (eles.empty()) return;
    let box = eles.boundingBox({ includeLabels: true });
    const pad = 36;
    const width = Math.max(core.width() - insets.left - insets.right - pad * 2, 80);
    const height = Math.max(core.height() - insets.top - insets.bottom - pad * 2, 80);
    // Small screens get a readable zoom (pan to explore) instead of a field of dots
    const fit = Math.min(width / box.w, height / box.h);
    if (fit < minZoom && anchor?.nonempty()) box = anchor.boundingBox({ includeLabels: true });
    const zoom = Math.min(Math.max(fit, minZoom), 1.35);
    const pan = {
      x: insets.left + pad + width / 2 - zoom * (box.x1 + box.w / 2),
      y: insets.top + pad + height / 2 - zoom * (box.y1 + box.h / 2),
    };
    // Replace any running camera move instead of queueing after it
    core.stop(true, false);
    if (animate && !reduceMotion) core.animate({ zoom, pan }, { duration: 550, easing: 'ease-in-out-cubic' });
    else core.viewport({ zoom, pan });
  }

  function highlight(core: Core, animate = true) {
    const selection = app.selection;
    core.batch(() => {
      core.elements().removeClass('dim focus onpath captioned hover-caption');
      core.edges().data('caption', '');
    });

    let focus = core.elements().not('.hidden');
    let anchor: cytoscape.Collection | undefined;
    let minZoom = core.width() < 760 ? 0.6 : core.minZoom();
    if (selection?.kind === 'node' && core.$id(selection.id).nonempty()) {
      const node = core.$id(selection.id);
      anchor = node;
      focus = node.closedNeighborhood().not('.hidden');
      core.batch(() => {
        core.elements().not(focus).addClass('dim');
        node.addClass('focus');
        const pin = focus.edges().length <= MAX_PINNED_CAPTIONS;
        focus.edges().forEach((edge) => {
          const other = edge.source().id() === selection.id ? edge.target().id() : edge.source().id();
          const data = pantheon.edges.find((candidate) => candidate.id === edge.id())!;
          edge.data('caption', roleLabel(data, pantheon.node(other)));
          if (pin) edge.addClass('captioned');
        });
      });
    } else if (selection?.kind === 'path' && path) {
      const ids = new Set([...path.nodes.map((node) => node.id), ...path.edges.map((edge) => edge.id)]);
      focus = core.elements().filter((element) => ids.has(element.id()));
      core.batch(() => {
        core.elements().not(focus).addClass('dim');
        focus.addClass('onpath');
        path!.edges.forEach((edge, index) => {
          core.$id(edge.id).data('caption', describeStep(edge, path!.nodes[index]!)).addClass('captioned');
        });
      });
    } else if (selection?.kind === 'path') {
      // No connection: show both ends
      focus = core.$id(selection.from).union(core.$id(selection.to));
      core.elements().not(focus).addClass('dim');
      focus.addClass('focus');
    } else if (selection === null) {
      // Overview: centre on the Olympians when the whole family cannot be read at once
      const olympus = core.$id('zeus');
      if (olympus.nonempty() && core.width() < 760) focus = olympus.closedNeighborhood();
    }
    if (selection?.kind === 'node') minZoom = 0.55;
    else if (selection) minZoom = core.minZoom();
    moveCamera(core, focus, { animate, minZoom, anchor });
  }

  // One selection changes several inputs in quick succession (the selection,
  // then the size of the panel that opens for it). Coalesce them into a single
  // camera move, and skip it when the target has not actually changed.
  let cameraTimer: ReturnType<typeof setTimeout> | undefined;
  let lastTarget = '';

  function moveCamera(core: Core, focus: cytoscape.Collection, options: Parameters<typeof frame>[2] = {}) {
    clearTimeout(cameraTimer);
    const target = [
      focus.map((element) => element.id()).sort().join(),
      app.layout,
      insets.top,
      insets.right,
      insets.bottom,
      insets.left,
    ].join('|');
    if (target === lastTarget) return;
    if (options.animate === false) {
      lastTarget = target;
      frame(core, focus, options);
      return;
    }
    cameraTimer = setTimeout(() => {
      lastTarget = target;
      frame(core, focus, options);
    }, 80);
  }

  onMount(() => {
    let disposed = false;
    // Canvas text needs the web font before the first paint
    const fonts = Promise.race([
      document.fonts.load(`700 16px ${LABEL_FONT}`),
      new Promise((resolve) => setTimeout(resolve, 1500)),
    ]);

    fonts.then(() => {
      if (disposed) return;
      const core = cytoscape({
        container,
        elements: elements(),
        style,
        minZoom: 0.12,
        maxZoom: 2.5,
        wheelSensitivity: 0.25,
        autoungrabify: true,
        boxSelectionEnabled: false,
      });
      core.on('tap', 'node', (event) => onselect(event.target.id()));
      core.on('tap', (event) => {
        if (event.target === core) onclear();
      });
      core.on('mouseover', 'node', (event) => {
        event.target.addClass('hover');
        event.target.connectedEdges('[caption != ""]').addClass('captioned hover-caption');
        container.style.cursor = 'pointer';
      });
      core.on('mouseout', 'node', (event) => {
        event.target.removeClass('hover');
        core.edges('.hover-caption').not('.onpath').removeClass('captioned hover-caption');
        container.style.cursor = '';
        if (app.selection?.kind === 'node') {
          const hood = core.$id(app.selection.id).connectedEdges();
          if (hood.length <= MAX_PINNED_CAPTIONS) hood.addClass('captioned');
        }
      });
      cy = core;
    });

    return () => {
      disposed = true;
      clearTimeout(cameraTimer);
      cy?.destroy();
    };
  });

  // Layout changes: move nodes, switch edge routing
  $effect(() => {
    const core = cy;
    const layout = app.layout;
    if (!core) return;
    const first = layouts.size === 0;
    const positions = positionsFor(core, layout);
    core.edges().toggleClass('tree', layout === 'tree');
    if (first || reduceMotion) {
      core.nodes().positions((node) => positions[node.id()]!);
      highlight(core, false);
    } else {
      core
        .layout({ name: 'preset', positions: (node: cytoscape.NodeSingular) => positions[node.id()]!, animate: true, animationDuration: 650, fit: false } as cytoscape.LayoutOptions)
        .run();
      setTimeout(() => highlight(core), 660);
    }
  });

  // Hidden relation kinds
  $effect(() => {
    const core = cy;
    const hidden = app.hiddenKinds;
    if (!core) return;
    core.edges().forEach((edge) => {
      edge.toggleClass('hidden', hidden.has(edge.data('kind')));
    });
  });

  // Selection, path and panel geometry
  $effect(() => {
    const core = cy;
    void app.selection;
    void path;
    void app.hiddenKinds;
    void insets.top, insets.right, insets.bottom, insets.left;
    if (core && layouts.size) highlight(core);
  });
</script>

<div class="canvas" bind:this={container} role="img" aria-label="Map of the Greek pantheon. Use the search or the cards to explore it."></div>

<style>
  .canvas {
    position: absolute;
    inset: 0;
  }
</style>
