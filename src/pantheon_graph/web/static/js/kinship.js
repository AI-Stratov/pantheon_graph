/**
 * Human wording for a chain of relationships: "son of", "great-grandson",
 * "cousins"... Gender comes from the node's `gender` property, or is implied
 * by the god/goddess kind; without it the neutral word is used.
 */

const KIND_GENDER = { god: 'male', goddess: 'female' };

const WORDS = {
  child: ['son', 'daughter', 'child'],
  parent: ['father', 'mother', 'parent'],
  spouse: ['husband', 'wife', 'spouse'],
  sibling: ['brother', 'sister', 'sibling'],
  nephew: ['nephew', 'niece', 'nibling'],
  uncle: ['uncle', 'aunt', 'parent’s sibling'],
};

export function genderOf(node) {
  return node.data('gender') ?? KIND_GENDER[node.data('kind')] ?? null;
}

/** Gendered word for a role, e.g. roleWord('parent', hera) === 'mother'. */
export function roleWord(role, node) {
  const [male, female, neutral] = WORDS[role];
  return { male, female }[genderOf(node)] ?? neutral;
}

/** The role ``node`` plays towards the other end of ``edge``: child, parent, spouse... */
export function roleOf(edge, node) {
  const kind = edge.data('kind');
  if (kind === 'parent') return edge.source().same(node) ? 'parent' : 'child';
  if (kind === 'spouse' || kind === 'sibling') return kind;
  return null;
}

/** "son of", "mother of", or the raw edge label for unknown relation kinds. */
export function describeStep(edge, node) {
  const role = roleOf(edge, node);
  if (!role) return edge.data('label') ?? edge.data('kind');
  // Keep source-specific nuance such as Wikidata's father/mother labels
  if (role === 'parent' && ['father', 'mother'].includes(edge.data('label'))) return `${edge.data('label')} of`;
  return `${roleWord(role, node)} of`;
}

const greats = (count) => 'great-'.repeat(Math.max(count, 0));

/**
 * One sentence about how the first and last node are related, given the
 * walk as [{ node, role }] where ``role`` is the node's role towards the next one.
 */
export function kinshipSentence(steps, last) {
  const first = steps[0].node;
  const a = first.data('label');
  const b = last.data('label');
  const roles = steps.map((step) => step.role);

  if (roles.length === 1 && roles[0]) return [a, `the ${roleWord(roles[0], first)} of`, b];

  // Pure lineage: some steps up the family tree, then some down
  const ups = roles.findIndex((role) => role !== 'child');
  const up = ups === -1 ? roles.length : ups;
  const down = roles.length - up;
  const isLineage = roles.slice(up).every((role) => role === 'parent');
  if (!isLineage) return null;

  if (down === 0) return [a, `the ${greats(up - 2)}${up > 1 ? 'grand' : ''}${roleWord('child', first)} of`, b];
  if (up === 0) return [a, `the ${greats(down - 2)}${down > 1 ? 'grand' : ''}${roleWord('parent', first)} of`, b];
  if (up === 1 && down === 1) return [a, `the ${roleWord('sibling', first)} of`, b];
  if (up === 2 && down === 1) return [a, `the ${roleWord('nephew', first)} of`, b];
  if (up === 1 && down === 2) return [a, `the ${roleWord('uncle', first)} of`, b];
  if (up === 2 && down === 2) return [a, 'the cousin of', b];
  return null;
}
