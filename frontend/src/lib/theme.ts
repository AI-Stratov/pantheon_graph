/** Visual vocabulary shared by the canvas and the HTML components. */
import type { NodeData } from './types';

export interface KindStyle {
  label: string;
  plural: string;
  /** Flat fill of the medallion; white text stays readable on every tone. */
  color: string;
  size: number;
}

// Tones of the Acropolis in daylight: Aegean sky, cloud shadow, terracotta,
// olive, sunlit ochre and limestone
export const KINDS: Record<string, KindStyle> = {
  primordial: { label: 'Primordial', plural: 'Primordials', color: '#6c6489', size: 50 },
  titan: { label: 'Titan', plural: 'Titans', color: '#b0623b', size: 42 },
  olympian: { label: 'Olympian', plural: 'Olympians', color: '#2f5d8a', size: 46 },
  deity: { label: 'Deity', plural: 'Deities', color: '#6b7a3f', size: 36 },
  hero: { label: 'Hero', plural: 'Heroes', color: '#9a7230', size: 36 },
  mortal: { label: 'Mortal', plural: 'Mortals', color: '#8f877a', size: 32 },
};

const FALLBACK: KindStyle = { label: 'Figure', plural: 'Other', color: '#8f877a', size: 34 };

// Older datasets (and databases seeded from them) split deities by gender
const LEGACY_KINDS: Record<string, string> = { god: 'deity', goddess: 'deity' };

export function kindStyle(kind: string | null): KindStyle {
  if (!kind) return FALLBACK;
  return KINDS[kind] ?? KINDS[LEGACY_KINDS[kind] ?? ''] ?? FALLBACK;
}

export const RELATIONS: Record<string, { label: string; color: string; dash: 'solid' | 'dashed' | 'dotted' }> = {
  parent: { label: 'Parent & child', color: '#8f8574', dash: 'solid' },
  spouse: { label: 'Married', color: '#b0623b', dash: 'dashed' },
  sibling: { label: 'Twins', color: '#6b7a3f', dash: 'dotted' },
};

export const RELATION_FALLBACK = { label: 'Related', color: '#8f8574', dash: 'solid' as const };

/** First letter of the Greek name without accents (Ἥρα → Η), or of the label. */
export function initial(node: NodeData): string {
  const greek = typeof node.properties.greek === 'string' ? node.properties.greek : node.label;
  return greek.normalize('NFD').replace(/\p{M}/gu, '').charAt(0).toLocaleUpperCase();
}

const svgCache = new Map<string, string>();

/** Medallion artwork for canvas nodes, as an SVG data URI. */
export function medallionSvg(node: NodeData): string {
  const { color } = kindStyle(node.kind);
  const letter = initial(node);
  const key = `${color}|${letter}`;
  const cached = svgCache.get(key);
  if (cached) return cached;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120" viewBox="0 0 120 120">
<circle cx="60" cy="60" r="58" fill="${color}"/>
<text x="60" y="78" text-anchor="middle" font-family="Georgia, 'DejaVu Serif', serif" font-size="50" fill="#fff">${letter}</text>
</svg>`;
  const uri = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
  svgCache.set(key, uri);
  return uri;
}
