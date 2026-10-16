import { expect, it } from 'vitest';

import { word } from './kinship';
import { initial, kindStyle, KINDS } from './theme';
import type { NodeData } from './types';

const node = (kind: string | null, properties: Record<string, unknown> = {}): NodeData => ({
  id: 'x',
  label: 'Zeus',
  kind,
  properties,
});

it('styles legacy god/goddess kinds as deities', () => {
  expect(kindStyle('god')).toBe(KINDS.deity);
  expect(kindStyle('goddess')).toBe(KINDS.deity);
  expect(kindStyle('olympian')).toBe(KINDS.olympian);
  expect(kindStyle('something-else').label).toBe('Figure');
  expect(kindStyle(null).label).toBe('Figure');
});

it('reads gender from legacy kinds when the property is missing', () => {
  expect(word('parent', node('goddess'))).toBe('mother');
  expect(word('child', node('god'))).toBe('son');
  expect(word('spouse', node('deity'))).toBe('spouse');
  expect(word('spouse', node('god', { gender: 'female' }))).toBe('wife');
});

it('takes the medallion letter from the Greek name without accents', () => {
  expect(initial(node('olympian', { greek: 'Ἥρα' }))).toBe('Η');
  expect(initial(node('olympian'))).toBe('Z');
});
