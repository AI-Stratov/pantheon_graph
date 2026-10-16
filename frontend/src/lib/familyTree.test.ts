import { expect, it } from 'vitest';

import { familyTree, generations } from './familyTree';
import { bundled } from './fixture.test-helper';

const pantheon = bundled();

it('puts every child below all of its parents', () => {
  const rows = generations(pantheon);
  for (const edge of pantheon.edges.filter((e) => e.kind === 'parent')) {
    expect(rows.get(edge.target)!, `${edge.source} → ${edge.target}`).toBeGreaterThan(rows.get(edge.source)!);
  }
});

it('lifts parentless partners to their partner’s generation', () => {
  const rows = generations(pantheon);
  expect(rows.get('gaia')).toBe(0);
  expect(rows.get('leda')).toBe(rows.get('zeus'));
  expect(rows.get('amphitrite')).toBe(rows.get('poseidon'));
});

it('lays out every node without overlaps', () => {
  const positions = familyTree(pantheon);
  expect(positions.size).toBe(pantheon.nodes.length);
  const keys = [...positions.values()].map(({ x, y }) => `${x},${y}`);
  expect(new Set(keys).size).toBe(keys.length);
});
