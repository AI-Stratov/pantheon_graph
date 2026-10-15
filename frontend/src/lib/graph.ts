import type { EdgeData, GraphData, NodeData } from './types';

export interface Path {
  nodes: NodeData[];
  /** ``edges[i]`` links ``nodes[i]`` and ``nodes[i + 1]``. */
  edges: EdgeData[];
}

export interface Relatives {
  parents: NodeData[];
  children: NodeData[];
  spouses: NodeData[];
  siblings: NodeData[];
}

const byLabel = (a: NodeData, b: NodeData) => a.label.localeCompare(b.label);

/** Read-only index over a graph snapshot with the queries the UI needs. */
export class Pantheon {
  readonly nodes: readonly NodeData[];
  readonly edges: readonly EdgeData[];
  readonly #byId: Map<string, NodeData>;
  readonly #edgesOf = new Map<string, EdgeData[]>();

  constructor(data: GraphData) {
    this.nodes = data.nodes;
    this.#byId = new Map(data.nodes.map((node) => [node.id, node]));
    // Edges to unknown nodes cannot be drawn or walked
    this.edges = data.edges.filter((edge) => this.#byId.has(edge.source) && this.#byId.has(edge.target));
    for (const edge of this.edges) {
      for (const end of [edge.source, edge.target]) {
        const list = this.#edgesOf.get(end) ?? [];
        list.push(edge);
        this.#edgesOf.set(end, list);
      }
    }
  }

  has(id: string): boolean {
    return this.#byId.has(id);
  }

  node(id: string): NodeData {
    const node = this.#byId.get(id);
    if (!node) throw new Error(`Unknown node ${id}`);
    return node;
  }

  edgesOf(id: string): readonly EdgeData[] {
    return this.#edgesOf.get(id) ?? [];
  }

  degree(id: string): number {
    return this.edgesOf(id).length;
  }

  /**
   * Fewest-hops chain between two nodes, ignoring direction.
   *
   * Neighbours are visited in ID order, exactly like ``Graph.shortest_path``
   * on the server, so both always pick the same chain among equal ones.
   */
  path(from: string, to: string, hiddenKinds: ReadonlySet<string> = new Set()): Path | null {
    if (!this.has(from) || !this.has(to)) return null;
    const previous = new Map<string, string | null>([[from, null]]);
    const queue = [from];
    for (let head = 0; head < queue.length && !previous.has(to); head += 1) {
      const current = queue[head]!;
      for (const next of this.#neighbours(current, hiddenKinds)) {
        if (!previous.has(next)) {
          previous.set(next, current);
          queue.push(next);
        }
      }
    }
    if (!previous.has(to)) return null;

    const chain = [to];
    for (let step = previous.get(to); step != null; step = previous.get(step)) chain.push(step);
    chain.reverse();
    return {
      nodes: chain.map((id) => this.node(id)),
      edges: chain.slice(1).map((id, index) => this.#edgeBetween(chain[index]!, id, hiddenKinds)),
    };
  }

  /** Parents, children and spouses from edges; siblings also from shared parents. */
  relatives(id: string): Relatives {
    const parents: NodeData[] = [];
    const children: NodeData[] = [];
    const spouses: NodeData[] = [];
    const siblings = new Map<string, NodeData>();
    for (const edge of this.edgesOf(id)) {
      const other = this.node(edge.source === id ? edge.target : edge.source);
      if (edge.kind === 'parent') (edge.target === id ? parents : children).push(other);
      else if (edge.kind === 'spouse') spouses.push(other);
      else if (edge.kind === 'sibling') siblings.set(other.id, other);
    }
    for (const parent of parents) {
      for (const edge of this.edgesOf(parent.id)) {
        if (edge.kind === 'parent' && edge.source === parent.id && edge.target !== id) {
          siblings.set(edge.target, this.node(edge.target));
        }
      }
    }
    return {
      parents: parents.sort(byLabel),
      children: children.sort(byLabel),
      spouses: spouses.sort(byLabel),
      siblings: [...siblings.values()].sort(byLabel),
    };
  }

  /** Case-insensitive search: exact and prefix matches first, then substrings. */
  search(query: string, limit = 8): NodeData[] {
    const needle = query.trim().toLocaleLowerCase();
    if (!needle) return [];
    const rank = (node: NodeData): number | null => {
      const label = node.label.toLocaleLowerCase();
      if (node.id.toLocaleLowerCase() === needle || label.startsWith(needle)) return 0;
      const greek = typeof node.properties.greek === 'string' ? node.properties.greek.toLocaleLowerCase() : '';
      if (label.includes(needle) || greek.includes(needle)) return 1;
      return null;
    };
    return this.nodes
      .map((node) => [rank(node), node] as const)
      .filter((entry): entry is readonly [number, NodeData] => entry[0] !== null)
      .sort((a, b) => a[0] - b[0])
      .slice(0, limit)
      .map(([, node]) => node);
  }

  /** Counts per node kind, most common first. */
  kinds(): [string, number][] {
    const counts = new Map<string, number>();
    for (const node of this.nodes) counts.set(node.kind ?? 'unknown', (counts.get(node.kind ?? 'unknown') ?? 0) + 1);
    return [...counts].sort((a, b) => b[1] - a[1]);
  }

  #neighbours(id: string, hiddenKinds: ReadonlySet<string>): string[] {
    const ids = new Set<string>();
    for (const edge of this.edgesOf(id)) {
      if (!hiddenKinds.has(edge.kind)) ids.add(edge.source === id ? edge.target : edge.source);
    }
    return [...ids].sort();
  }

  #edgeBetween(a: string, b: string, hiddenKinds: ReadonlySet<string>): EdgeData {
    const edge = this.edges.find(
      (e) => !hiddenKinds.has(e.kind) && ((e.source === a && e.target === b) || (e.source === b && e.target === a)),
    );
    if (!edge) throw new Error(`No edge between ${a} and ${b}`);
    return edge;
  }
}
