import { expect, it } from 'vitest';

import { AppState } from './state.svelte';

const known = (id: string) => ['zeus', 'hera'].includes(id);

it('round-trips through the query string', () => {
  const state = new AppState();
  state.connect('zeus', 'hera');
  state.layout = 'tree';
  state.toggleKind('spouse');

  const restored = new AppState();
  restored.fromQuery(state.toQuery(), known);

  expect(state.toQuery()).toBe('?layout=tree&from=zeus&to=hera&hide=spouse');
  expect(restored.selection).toEqual({ kind: 'path', from: 'zeus', to: 'hera' });
  expect(restored.layout).toBe('tree');
  expect([...restored.hiddenKinds]).toEqual(['spouse']);
});

it('ignores unknown nodes and junk', () => {
  const state = new AppState();
  state.fromQuery('?node=odin&layout=spiral&hide=parent,bogus', known);

  expect(state.selection).toBeNull();
  expect(state.layout).toBe('constellation');
  expect([...state.hiddenKinds]).toEqual(['parent']);
  expect(state.toQuery()).toBe('?hide=parent');
});

it('treats a path to oneself as a selection', () => {
  const state = new AppState();
  state.connect('zeus', 'zeus');
  expect(state.selection).toEqual({ kind: 'node', id: 'zeus' });
});
