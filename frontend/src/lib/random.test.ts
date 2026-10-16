import { expect, it } from 'vitest';

import { seededRandom, withSeed } from './random';

it('is deterministic and restores Math.random', () => {
  const original = Math.random;
  const a = withSeed(7, () => [Math.random(), Math.random()]);
  const b = withSeed(7, () => [Math.random(), Math.random()]);
  expect(a).toEqual(b);
  expect(Math.random).toBe(original);
  expect(seededRandom(1)()).not.toBe(seededRandom(2)());
});
