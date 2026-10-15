import { describe, expect, it } from 'vitest';

import { bundled } from './fixture.test-helper';
import { Pantheon } from './graph';

const pantheon = bundled();
const ids = (nodes: { id: string }[]) => nodes.map((node) => node.id);

describe('Pantheon.path', () => {
  it('walks the shortest chain in ID order, like the server', () => {
    const path = pantheon.path('heracles', 'uranus')!;
    // Cronus < Rhea: same tie-break as Python's sorted() neighbours
    expect(ids(path.nodes)).toEqual(['heracles', 'zeus', 'cronus', 'uranus']);
    expect(path.edges.map((edge) => edge.kind)).toEqual(['parent', 'parent', 'parent']);
  });

  it('respects hidden relation kinds', () => {
    expect(pantheon.path('hephaestus', 'hermes')!.nodes).toHaveLength(4);
    expect(pantheon.path('hephaestus', 'hermes', new Set(['parent']))).toBeNull();
  });

  it('handles trivial and unknown endpoints', () => {
    expect(ids(pantheon.path('zeus', 'zeus')!.nodes)).toEqual(['zeus']);
    expect(pantheon.path('zeus', 'odin')).toBeNull();
  });
});

describe('Pantheon.relatives', () => {
  it('derives siblings from shared parents', () => {
    const zeus = pantheon.relatives('zeus');
    expect(ids(zeus.parents)).toEqual(['cronus', 'rhea']);
    expect(ids(zeus.siblings)).toEqual(['demeter', 'hades', 'hera', 'hestia', 'poseidon']);
    expect(ids(zeus.spouses)).toEqual(['hera', 'metis', 'themis']);
    expect(zeus.children.length).toBeGreaterThan(10);
  });
});

describe('Pantheon.search', () => {
  it('ranks prefixes first and also matches Greek names', () => {
    expect(ids(pantheon.search('he', 4))).toEqual(['helios', 'hera', 'hestia', 'hephaestus']);
    expect(ids(pantheon.search('Ζεύς'))).toEqual(['zeus']);
    expect(pantheon.search('   ')).toEqual([]);
  });
});

it('drops edges pointing at unknown nodes', () => {
  const graph = new Pantheon({
    nodes: [{ id: 'a', label: 'A', kind: null, properties: {} }],
    edges: [{ id: 'e', source: 'a', target: 'ghost', kind: 'parent', label: null, properties: {} }],
  });
  expect(graph.edges).toEqual([]);
});
