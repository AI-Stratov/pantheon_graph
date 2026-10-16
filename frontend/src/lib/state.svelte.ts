/** UI state that is worth sharing: everything here round-trips through the URL. */

export type Layout = 'constellation' | 'tree';

export type Selection = { kind: 'node'; id: string } | { kind: 'path'; from: string; to: string } | null;

const RELATION_KINDS = ['parent', 'spouse', 'sibling'];

export class AppState {
  selection = $state<Selection>(null);
  layout = $state<Layout>('constellation');
  hiddenKinds = $state(new Set<string>());

  select(id: string) {
    this.selection = { kind: 'node', id };
  }

  connect(from: string, to: string) {
    this.selection = from === to ? { kind: 'node', id: from } : { kind: 'path', from, to };
  }

  clear() {
    this.selection = null;
  }

  toggleKind(kind: string) {
    const next = new Set(this.hiddenKinds);
    if (!next.delete(kind)) next.add(kind);
    this.hiddenKinds = next;
  }

  toQuery(): string {
    const params = new URLSearchParams();
    if (this.layout !== 'constellation') params.set('layout', this.layout);
    if (this.selection?.kind === 'node') params.set('node', this.selection.id);
    if (this.selection?.kind === 'path') {
      params.set('from', this.selection.from);
      params.set('to', this.selection.to);
    }
    if (this.hiddenKinds.size) params.set('hide', [...this.hiddenKinds].sort().join(','));
    const query = params.toString();
    return query ? `?${query}` : '';
  }

  /** Apply a query string; unknown node IDs are ignored by ``isKnown``. */
  fromQuery(query: string, isKnown: (id: string) => boolean) {
    const params = new URLSearchParams(query);
    this.layout = params.get('layout') === 'tree' ? 'tree' : 'constellation';
    this.hiddenKinds = new Set((params.get('hide') ?? '').split(',').filter((kind) => RELATION_KINDS.includes(kind)));
    const [node, from, to] = ['node', 'from', 'to'].map((key) => params.get(key));
    if (from && to && isKnown(from) && isKnown(to)) this.connect(from, to);
    else if (node && isKnown(node)) this.select(node);
    else this.selection = null;
  }
}
