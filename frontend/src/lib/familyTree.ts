/**
 * Generational layout: ancestors on top, one row per generation.
 *
 * - a node's generation is the longest chain of parent edges above it, so a
 *   child is always drawn below both of its parents;
 * - a partner with no known parents joins the row of the partner it had
 *   children with (or married) instead of floating at the top;
 * - each row is ordered by the mean position of the parents above it
 *   (barycenter heuristic) and partners are kept next to each other.
 */
import type { Pantheon } from './graph';

export interface Point {
  x: number;
  y: number;
}

export const H_GAP = 110;
export const V_GAP = 150;

export function generations(pantheon: Pantheon): Map<string, number> {
  const parentEdges = pantheon.edges.filter((edge) => edge.kind === 'parent');
  const generation = new Map(pantheon.nodes.map((node) => [node.id, 0]));

  // Longest-path relaxation; bounded so cyclic bad data cannot hang the page
  for (let round = 0; round < pantheon.nodes.length; round += 1) {
    let changed = false;
    for (const edge of parentEdges) {
      const below = generation.get(edge.source)! + 1;
      if (below > generation.get(edge.target)!) {
        generation.set(edge.target, below);
        changed = true;
      }
    }
    if (!changed) break;
  }

  for (const node of pantheon.nodes) {
    const { parents, children, spouses } = pantheon.relatives(node.id);
    if (parents.length > 0) continue;
    const coParents = children.flatMap((child) => pantheon.relatives(child.id).parents);
    const anchored = [...coParents, ...spouses].filter(
      (partner) => partner.id !== node.id && pantheon.relatives(partner.id).parents.length > 0,
    );
    if (anchored.length > 0) {
      generation.set(node.id, Math.max(...anchored.map((partner) => generation.get(partner.id)!)));
    } else if (children.length > 0) {
      generation.set(node.id, Math.min(...children.map((child) => generation.get(child.id)!)) - 1);
    }
  }

  // Rows start at 0 even if a partner was pulled above the first generation
  const top = Math.min(...generation.values());
  for (const [id, row] of generation) generation.set(id, row - top);
  return generation;
}

export function familyTree(pantheon: Pantheon): Map<string, Point> {
  const generation = generations(pantheon);
  const rows = new Map<number, string[]>();
  for (const node of pantheon.nodes) {
    const row = generation.get(node.id)!;
    rows.set(row, [...(rows.get(row) ?? []), node.id]);
  }

  const partnersOf = (id: string) => {
    const { spouses, children } = pantheon.relatives(id);
    const coParents = children.flatMap((child) => pantheon.relatives(child.id).parents);
    return new Set([...spouses, ...coParents].map((node) => node.id).filter((other) => other !== id));
  };

  const column = new Map<string, number>();
  const positions = new Map<string, Point>();
  for (const row of [...rows.keys()].sort((a, b) => a - b)) {
    const members = rows.get(row)!;
    const barycenter = (id: string) => {
      const placed = pantheon.relatives(id).parents.filter((parent) => column.has(parent.id));
      if (placed.length === 0) return null;
      return placed.reduce((sum, parent) => sum + column.get(parent.id)!, 0) / placed.length;
    };

    const anchored = members
      .map((id) => [id, barycenter(id)] as const)
      .filter((entry): entry is readonly [string, number] => entry[1] !== null)
      .sort((a, b) => a[1] - b[1])
      .map(([id]) => id);
    const ordered = [...anchored];
    // Partners without parents of their own sit right next to their partner
    for (const id of members.filter((member) => barycenter(member) === null)) {
      const partners = partnersOf(id);
      const at = ordered.findLastIndex((other) => partners.has(other));
      ordered.splice(at === -1 ? ordered.length : at + 1, 0, id);
    }

    ordered.forEach((id, index) => {
      const x = (index - (ordered.length - 1) / 2) * H_GAP;
      column.set(id, x);
      positions.set(id, { x, y: row * V_GAP });
    });
  }
  return positions;
}
