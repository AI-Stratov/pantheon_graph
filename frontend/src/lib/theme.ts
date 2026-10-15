/** Visual vocabulary shared by the canvas and the HTML components. */
import type { NodeData } from './types';

export interface KindStyle {
  label: string;
  plural: string;
  /** Main tone, also used for the glow. */
  color: string;
  /** Darker edge of the medallion gradient. */
  shade: string;
  size: number;
}

export const KINDS: Record<string, KindStyle> = {
  primordial: { label: 'Primordial', plural: 'Primordials', color: '#9d8cff', shade: '#2b2160', size: 54 },
  titan: { label: 'Titan', plural: 'Titans', color: '#d08f4f', shade: '#4a2a12', size: 44 },
  olympian: { label: 'Olympian', plural: 'Olympians', color: '#ecc65f', shade: '#5a4210', size: 50 },
  deity: { label: 'Deity', plural: 'Deities', color: '#6fc3cf', shade: '#123c45', size: 38 },
  hero: { label: 'Hero', plural: 'Heroes', color: '#e7765e', shade: '#4d1a12', size: 38 },
  mortal: { label: 'Mortal', plural: 'Mortals', color: '#a4adbf', shade: '#2a3040', size: 34 },
};

const FALLBACK: KindStyle = { label: 'Figure', plural: 'Other', color: '#b9b3a3', shade: '#2d2b26', size: 36 };

export function kindStyle(kind: string | null): KindStyle {
  return (kind && KINDS[kind]) || FALLBACK;
}

export const RELATIONS: Record<string, { label: string; color: string; dash: 'solid' | 'dashed' | 'dotted' }> = {
  parent: { label: 'Parent & child', color: '#d9b45a', dash: 'solid' },
  spouse: { label: 'Married', color: '#e98aa0', dash: 'dashed' },
  sibling: { label: 'Twins', color: '#7fd1c1', dash: 'dotted' },
};

export const RELATION_FALLBACK = { label: 'Related', color: '#b9b3a3', dash: 'solid' as const };

/** First letter of the Greek name without accents (Ἥρα → Η), or of the label. */
export function initial(node: NodeData): string {
  const greek = typeof node.properties.greek === 'string' ? node.properties.greek : node.label;
  return greek.normalize('NFD').replace(/\p{M}/gu, '').charAt(0).toLocaleUpperCase();
}

const svgCache = new Map<string, string>();

/** Medallion artwork for canvas nodes, as an SVG data URI. */
export function medallionSvg(node: NodeData): string {
  const { color, shade } = kindStyle(node.kind);
  const letter = initial(node);
  const key = `${color}|${letter}`;
  const cached = svgCache.get(key);
  if (cached) return cached;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120" viewBox="0 0 120 120">
<defs><radialGradient id="g" cx="50%" cy="32%" r="70%"><stop offset="0" stop-color="${color}"/><stop offset="0.55" stop-color="${shade}"/><stop offset="1" stop-color="#05070f"/></radialGradient></defs>
<circle cx="60" cy="60" r="55" fill="url(#g)"/>
<circle cx="60" cy="60" r="55" fill="none" stroke="${color}" stroke-width="5"/>
<circle cx="60" cy="60" r="45" fill="none" stroke="#fff6dc" stroke-opacity="0.22" stroke-width="1.5"/>
<text x="60" y="78" text-anchor="middle" font-family="Georgia, 'DejaVu Serif', serif" font-size="50" fill="#fff8e6">${letter}</text>
</svg>`;
  const uri = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
  svgCache.set(key, uri);
  return uri;
}
