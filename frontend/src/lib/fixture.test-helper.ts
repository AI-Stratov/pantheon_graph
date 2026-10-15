/** The bundled dataset in wire format, built the same way as MemorySource does. */
import dataset from '../../../src/pantheon_graph/infrastructure/sources/data/pantheon.json';
import { Pantheon } from './graph';
import type { EdgeData, GraphData } from './types';

type Dataset = {
  nodes: ({ id: string; label: string; kind: string } & Record<string, unknown>)[];
  parents: { parents: string[]; children: string[] }[];
  spouses: [string, string][];
  siblings: [string, string][];
};

function edge(source: string, target: string, kind: string): EdgeData {
  if (kind !== 'parent') [source, target] = [source, target].sort() as [string, string];
  return { id: `${source}-${target}-${kind}`, source, target, kind, label: kind, properties: {} };
}

export function bundled(): Pantheon {
  const data = dataset as unknown as Dataset;
  const graph: GraphData = {
    nodes: data.nodes.map(({ id, label, kind, ...properties }) => ({ id, label, kind, properties })),
    edges: [
      ...data.parents.flatMap(({ parents, children }) =>
        parents.flatMap((parent) => children.map((child) => edge(parent, child, 'parent'))),
      ),
      ...data.spouses.map(([a, b]) => edge(a, b, 'spouse')),
      ...data.siblings.map(([a, b]) => edge(a, b, 'sibling')),
    ],
  };
  return new Pantheon(graph);
}
