import { describe, expect, it } from 'vitest';

import { bundled } from './fixture.test-helper';
import { describeStep, kinship } from './kinship';

const pantheon = bundled();

function relation(from: string, to: string): string | null {
  return kinship(pantheon.path(from, to)!, pantheon).relation;
}

describe('kinship', () => {
  it.each([
    ['heracles', 'zeus', 'son'],
    ['zeus', 'heracles', 'father'],
    ['hera', 'zeus', 'wife'],
    ['heracles', 'uranus', 'great-grandson'],
    ['uranus', 'heracles', 'great-grandfather'],
    ['athena', 'cronus', 'granddaughter'],
    ['zeus', 'hera', 'husband'], // also her brother, but marriage is the direct tie
    ['poseidon', 'hades', 'brother'],
    ['athena', 'ares', 'half-sister'],
    ['apollo', 'artemis', 'brother'],
    ['persephone', 'hades', 'wife'],
    ['athena', 'hades', 'niece'],
    ['hades', 'athena', 'uncle'],
    ['hephaestus', 'zeus', 'stepson'],
    ['zeus', 'hephaestus', 'stepfather'],
    ['cadmus', 'aphrodite', 'son-in-law'],
    ['harmonia', 'eros', 'sister'],
    ['dionysus', 'harmonia', 'grandson'],
  ])('%s → %s: %s', (from, to, expected) => {
    expect(relation(from, to)).toBe(expected);
  });

  it('names cousins of the same generation', () => {
    expect(relation('helios', 'zeus')).toBe('cousin');
  });

  it('falls back to "connected through" for winding paths', () => {
    const result = kinship(pantheon.path('triton', 'prometheus')!, pantheon);
    expect(result.relation).toBeNull();
    expect(result.via.map((node) => node.id)).toEqual(['poseidon', 'cronus', 'gaia', 'iapetus']);
  });

  it('keeps separate lineages apart', () => {
    expect(pantheon.path('eris', 'zeus')).toBeNull(); // Hesiod's Night bore her alone
  });

  it('describes single steps from the walker’s side', () => {
    const [edge] = pantheon.path('heracles', 'zeus')!.edges;
    expect(describeStep(edge!, pantheon.node('heracles'))).toBe('son of');
    expect(describeStep(edge!, pantheon.node('zeus'))).toBe('father of');
  });
});
