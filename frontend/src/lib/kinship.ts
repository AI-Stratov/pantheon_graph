/**
 * Plain-English wording for family ties: "son of", "great-grandson",
 * "half-sister", "stepmother"... Gendered words use the node's `gender`
 * property and fall back to neutral ones ("child", "parent").
 */
import type { Pantheon, Path } from './graph';
import { genderOf, type EdgeData, type NodeData } from './types';

export type Role = 'child' | 'parent' | 'spouse' | 'sibling';

type Words = readonly [male: string, female: string, neutral: string];

const WORDS: Record<string, Words> = {
  child: ['son', 'daughter', 'child'],
  parent: ['father', 'mother', 'parent'],
  spouse: ['husband', 'wife', 'spouse'],
  sibling: ['brother', 'sister', 'sibling'],
  nephew: ['nephew', 'niece', 'nibling'],
  uncle: ['uncle', 'aunt', 'parent’s sibling'],
  cousin: ['cousin', 'cousin', 'cousin'],
};

/** Gendered word, e.g. ``word('parent', hera) === 'mother'``. */
export function word(kind: keyof typeof WORDS, node: NodeData): string {
  const [male, female, neutral] = WORDS[kind]!;
  const gender = genderOf(node);
  return gender === 'male' ? male : gender === 'female' ? female : neutral;
}

/** The role ``nodeId`` plays towards the other end of ``edge``. */
export function roleOf(edge: EdgeData, nodeId: string): Role | null {
  if (edge.kind === 'parent') return edge.source === nodeId ? 'parent' : 'child';
  if (edge.kind === 'spouse' || edge.kind === 'sibling') return edge.kind;
  return null;
}

/** How ``node`` relates to the next node across ``edge``: "son of", "wife of"... */
export function describeStep(edge: EdgeData, node: NodeData): string {
  const role = roleOf(edge, node.id);
  if (!role) return edge.label ?? edge.kind;
  return `${word(role, node)} of`;
}

/** Short role of ``node`` towards its neighbour across ``edge``: "father", "wife"... */
export function roleLabel(edge: EdgeData, node: NodeData): string {
  const role = roleOf(edge, node.id);
  return role ? word(role, node) : (edge.label ?? edge.kind);
}

export interface Kinship {
  from: NodeData;
  to: NodeData;
  /** "great-grandson", "half-sister"...; null when there is no simple name for it. */
  relation: string | null;
  /** The figures in between. */
  via: NodeData[];
}

const greats = (count: number) => 'great-'.repeat(Math.max(count, 0));

function sameParents(pantheon: Pantheon, a: string, b: string): boolean {
  const ids = (id: string) => pantheon.relatives(id).parents.map((p) => p.id).sort().join();
  return ids(a) === ids(b) && pantheon.relatives(a).parents.length > 1;
}

/** Name the relationship walked by ``path``, read as "from is the <relation> of to". */
export function kinship(path: Path, pantheon?: Pantheon): Kinship {
  const from = path.nodes[0]!;
  const to = path.nodes.at(-1)!;
  const via = path.nodes.slice(1, -1);
  const roles = path.edges.map((edge, index) => roleOf(edge, path.nodes[index]!.id));
  const named = (relation: string | null): Kinship => ({ from, to, relation, via });

  if (roles.length === 0 || roles.includes(null)) return named(null);
  const pattern = roles.join(' ');

  switch (pattern) {
    case 'child':
    case 'parent':
    case 'spouse':
    case 'sibling':
      return named(word(roles[0]!, from));
    case 'child spouse':
      return named(`step${word('child', from)}`);
    case 'spouse parent':
      return named(`step${word('parent', from)}`);
    case 'spouse child':
      return named(`${word('child', from)}-in-law`);
    case 'parent spouse':
      return named(`${word('parent', from)}-in-law`);
  }

  // Straight bloodline: some generations up, then some down
  const up = roles.findIndex((role) => role !== 'child');
  const ups = up === -1 ? roles.length : up;
  const downs = roles.length - ups;
  if (!roles.slice(ups).every((role) => role === 'parent')) return named(null);

  if (downs === 0) return named(`${greats(ups - 2)}${ups > 1 ? 'grand' : ''}${word('child', from)}`);
  if (ups === 0) return named(`${greats(downs - 2)}${downs > 1 ? 'grand' : ''}${word('parent', from)}`);
  if (ups === 1 && downs === 1) {
    const full = pantheon ? sameParents(pantheon, from.id, to.id) : false;
    return named(`${full ? '' : 'half-'}${word('sibling', from)}`);
  }
  if (downs === 1) return named(`${greats(ups - 3)}${ups > 2 ? 'grand' : ''}${word('nephew', from)}`);
  if (ups === 1) return named(`${greats(downs - 3)}${downs > 2 ? 'grand' : ''}${word('uncle', from)}`);
  if (ups === downs) return named(ups === 2 ? 'cousin' : `${ordinal(ups - 1)} cousin`);
  return named(null);
}

function ordinal(n: number): string {
  return ['first', 'second', 'third', 'fourth', 'fifth'][n - 1] ?? `${n}th`;
}
