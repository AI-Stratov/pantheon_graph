<script lang="ts">
  import type { Pantheon } from '../lib/graph';
  import { kindStyle } from '../lib/theme';
  import { text, type NodeData } from '../lib/types';
  import Medallion from './Medallion.svelte';

  interface Props {
    pantheon: Pantheon;
    label: string;
    placeholder?: string;
    value?: NodeData | null;
    onpick: (node: NodeData) => void;
    clearOnPick?: boolean;
    testid?: string;
  }

  let { pantheon, label, placeholder = '', value = null, onpick, clearOnPick = false, testid }: Props = $props();

  const listId = `picker-${Math.random().toString(36).slice(2)}`;
  let query = $state('');
  let open = $state(false);
  let active = $state(0);
  let input: HTMLInputElement;

  // Show the chosen node's name until the user types something else
  $effect(() => {
    query = value?.label ?? '';
  });

  const results = $derived(open ? pantheon.search(query, 7) : []);

  function pick(node: NodeData) {
    onpick(node);
    query = clearOnPick ? '' : node.label;
    open = false;
    input.blur();
  }

  function onkeydown(event: KeyboardEvent) {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      open = true;
      const step = event.key === 'ArrowDown' ? 1 : -1;
      active = (active + step + results.length) % Math.max(results.length, 1);
    } else if (event.key === 'Enter' && results[active]) {
      event.preventDefault();
      pick(results[active]!);
    } else if (event.key === 'Escape') {
      open = false;
      query = value?.label ?? '';
    }
  }
</script>

<div class="picker">
  <label class="visually-hidden" for="{listId}-input">{label}</label>
  <input
    bind:this={input}
    id="{listId}-input"
    data-testid={testid}
    type="search"
    role="combobox"
    autocomplete="off"
    spellcheck="false"
    aria-expanded={results.length > 0}
    aria-controls={listId}
    aria-activedescendant={results.length ? `${listId}-${active}` : undefined}
    {placeholder}
    bind:value={query}
    oninput={() => {
      open = true;
      active = 0;
    }}
    onfocus={(event) => {
      open = true;
      (event.currentTarget as HTMLInputElement).select();
    }}
    onblur={() => setTimeout(() => (open = false), 120)}
    {onkeydown}
  />
  {#if results.length}
    <ul class="results surface" id={listId} role="listbox">
      {#each results as node, index (node.id)}
        <li
          id="{listId}-{index}"
          role="option"
          aria-selected={index === active}
          class:active={index === active}
          onpointerdown={(event) => {
            event.preventDefault();
            pick(node);
          }}
          onpointerenter={() => (active = index)}
        >
          <Medallion {node} size={30} />
          <span class="name">{node.label}</span>
          <span class="meta">{text(node, 'greek') ?? ''} · {kindStyle(node.kind).label}</span>
        </li>
      {/each}
    </ul>
  {/if}
</div>

<style>
  .picker {
    position: relative;
  }

  input {
    width: 100%;
    padding: 10px 16px;
    border: 1px solid var(--line-strong);
    border-radius: 999px;
    background: var(--surface);
    color: var(--ink);
    font-size: 15px;
  }

  input::placeholder {
    color: var(--ink-muted);
  }

  input:focus {
    border-color: var(--sky);
    outline: none;
    box-shadow: 0 0 0 3px var(--sky-soft);
  }

  .results {
    position: absolute;
    z-index: 30;
    top: calc(100% + 6px);
    right: 0;
    left: 0;
    margin: 0;
    padding: 6px;
    list-style: none;
    border-radius: var(--radius-sm);
  }

  li {
    display: grid;
    grid-template-columns: auto 1fr;
    grid-template-rows: auto auto;
    column-gap: 10px;
    align-items: center;
    padding: 6px 8px;
    border-radius: 8px;
    cursor: pointer;
  }

  li.active {
    background: var(--sky-soft);
  }

  li :global(.medallion) {
    grid-row: span 2;
  }

  .name {
    font: 700 17px/1.1 var(--font-serif);
  }

  .meta {
    color: var(--ink-muted);
    font-size: 12px;
  }
</style>
