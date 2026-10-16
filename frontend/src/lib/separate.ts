/**
 * Push apart boxes that overlap, keeping everything else where it is.
 *
 * Force-directed layouts pull tightly related nodes (a couple with many
 * children) on top of each other; this pass guarantees that medallions and
 * their names stay readable. Boxes are moved along the axis of least overlap,
 * half each, until no pair overlaps or the iteration budget runs out.
 */
export interface Box {
  id: string;
  /** Centre of the box. */
  x: number;
  y: number;
  width: number;
  height: number;
}

// A little extra per push so boxes clear each other instead of creeping into contact
const NUDGE = 0.5;

export function separate(boxes: readonly Box[], gap = 8, maxRounds = 200): Map<string, { x: number; y: number }> {
  const items = boxes.map((box) => ({ ...box }));
  for (let round = 0; round < maxRounds; round += 1) {
    let moved = false;
    for (let i = 0; i < items.length; i += 1) {
      for (let j = i + 1; j < items.length; j += 1) {
        const a = items[i]!;
        const b = items[j]!;
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const overlapX = (a.width + b.width) / 2 + gap - Math.abs(dx);
        const overlapY = (a.height + b.height) / 2 + gap - Math.abs(dy);
        if (overlapX <= 0 || overlapY <= 0) continue;
        moved = true;
        // Resolve along the cheaper axis; ties (identical centres) go sideways
        if (overlapX < overlapY) {
          const shift = (overlapX / 2 + NUDGE) * (dx < 0 ? -1 : 1);
          a.x -= shift;
          b.x += shift;
        } else {
          const shift = (overlapY / 2 + NUDGE) * (dy < 0 ? -1 : 1);
          a.y -= shift;
          b.y += shift;
        }
      }
    }
    if (!moved) break;
  }
  return new Map(items.map(({ id, x, y }) => [id, { x, y }]));
}
