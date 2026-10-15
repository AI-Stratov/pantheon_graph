/**
 * Generational layout: ancestors on top, each generation on its own row.
 *
 * - a node's generation is the longest chain of parent edges above it, so a
 *   child always sits below both of its parents;
 * - a partner without known parents joins the row of its children's other
 *   parent (or of its spouse) instead of floating at the top;
 * - inside a row, nodes are ordered by the mean position of their parents
 *   (barycenter heuristic) to keep edges from crossing.
 */
const H_GAP = 120;
const V_GAP = 140;

export function familyTreePositions(cy) {
  const nodes = cy.nodes();
  const parentEdges = cy.edges('[kind = "parent"]');
  const parentsOf = (node) => parentEdges.filter((e) => e.target().same(node)).sources();
  const childrenOf = (node) => parentEdges.filter((e) => e.source().same(node)).targets();
  const partnersOf = (node) =>
    node
      .connectedEdges('[kind = "spouse"]')
      .connectedNodes()
      .union(childrenOf(node).map(parentsOf).reduce((all, p) => all.union(p), cy.collection()))
      .not(node);

  const generation = new Map(nodes.map((node) => [node.id(), 0]));
  // Longest-path relaxation; bounded by node count so cycles in bad data cannot hang
  for (let round = 0; round < nodes.length; round += 1) {
    let changed = false;
    parentEdges.forEach((edge) => {
      const below = generation.get(edge.source().id()) + 1;
      if (below > generation.get(edge.target().id())) {
        generation.set(edge.target().id(), below);
        changed = true;
      }
    });
    if (!changed) break;
  }

  nodes.forEach((node) => {
    if (parentsOf(node).nonempty()) return;
    const partners = partnersOf(node).filter((p) => parentsOf(p).nonempty());
    if (partners.nonempty()) {
      generation.set(node.id(), Math.max(...partners.map((p) => generation.get(p.id()))));
    } else if (childrenOf(node).nonempty()) {
      generation.set(node.id(), Math.min(...childrenOf(node).map((c) => generation.get(c.id()))) - 1);
    }
  });

  const rows = new Map();
  nodes.forEach((node) => {
    const row = generation.get(node.id());
    if (!rows.has(row)) rows.set(row, []);
    rows.get(row).push(node);
  });

  const column = new Map();
  const positions = {};
  for (const row of [...rows.keys()].sort((a, b) => a - b)) {
    const members = rows.get(row);
    const barycenter = (node) => {
      const placed = parentsOf(node).filter((p) => column.has(p.id()));
      return placed.empty() ? Infinity : placed.reduce((sum, p) => sum + column.get(p.id()), 0) / placed.length;
    };
    const ordered = members.filter((n) => barycenter(n) !== Infinity).sort((a, b) => barycenter(a) - barycenter(b));
    for (const node of members.filter((n) => barycenter(n) === Infinity)) {
      const partner = ordered.findIndex((other) => partnersOf(node).contains(other));
      ordered.splice(partner === -1 ? ordered.length : partner + 1, 0, node);
    }
    ordered.forEach((node, index) => {
      const x = (index - (ordered.length - 1) / 2) * H_GAP;
      column.set(node.id(), x);
      positions[node.id()] = { x, y: row * V_GAP };
    });
  }
  return positions;
}
