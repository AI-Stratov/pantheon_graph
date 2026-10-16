import { expect, it } from 'vitest';

import { type Box, separate } from './separate';

const overlaps = (boxes: Box[], positions: Map<string, { x: number; y: number }>, gap: number) =>
  boxes.some((a, i) =>
    boxes.slice(i + 1).some((b) => {
      const pa = positions.get(a.id)!;
      const pb = positions.get(b.id)!;
      return (
        Math.abs(pa.x - pb.x) < (a.width + b.width) / 2 + gap - 1e-6 &&
        Math.abs(pa.y - pb.y) < (a.height + b.height) / 2 + gap - 1e-6
      );
    }),
  );

it('separates overlapping boxes and leaves distant ones alone', () => {
  const boxes: Box[] = [
    { id: 'cronus', x: 0, y: 0, width: 60, height: 70 },
    { id: 'rhea', x: 20, y: 10, width: 60, height: 70 },
    { id: 'far', x: 500, y: 500, width: 60, height: 70 },
  ];
  const positions = separate(boxes, 8);

  expect(overlaps(boxes, positions, 8)).toBe(false);
  expect(positions.get('far')).toEqual({ x: 500, y: 500 });
  // Moved symmetrically along the cheaper axis
  expect(positions.get('cronus')!.x).toBeLessThan(0);
  expect(positions.get('rhea')!.x).toBeGreaterThan(20);
});

it('untangles a crowded cluster', () => {
  const boxes: Box[] = Array.from({ length: 30 }, (_, i) => ({
    id: String(i),
    x: (i % 5) * 10,
    y: Math.floor(i / 5) * 10,
    width: 50,
    height: 60,
  }));
  expect(overlaps(boxes, separate(boxes, 6), 6)).toBe(false);
});

it('pulls apart boxes sharing the same centre', () => {
  const boxes: Box[] = [
    { id: 'a', x: 0, y: 0, width: 40, height: 40 },
    { id: 'b', x: 0, y: 0, width: 40, height: 40 },
  ];
  expect(overlaps(boxes, separate(boxes, 4), 4)).toBe(false);
});
