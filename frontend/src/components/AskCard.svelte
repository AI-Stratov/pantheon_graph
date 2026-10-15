<script lang="ts">
  import type { Pantheon } from '../lib/graph';
  import type { NodeData } from '../lib/types';
  import NodePicker from './NodePicker.svelte';

  interface Props {
    pantheon: Pantheon;
    onconnect: (from: string, to: string) => void;
  }

  let { pantheon, onconnect }: Props = $props();

  // Showcase questions; pairs missing from the loaded data are skipped
  const EXAMPLES: [string, string][] = [
    ['heracles', 'uranus'],
    ['athena', 'hades'],
    ['hephaestus', 'zeus'],
    ['helen', 'apollo'],
    ['dionysus', 'harmonia'],
  ];

  let from = $state<NodeData | null>(null);
  let to = $state<NodeData | null>(null);
  const examples = $derived(
    EXAMPLES.filter(([a, b]) => pantheon.has(a) && pantheon.has(b)).map(([a, b]) => [pantheon.node(a), pantheon.node(b)] as const),
  );

  function submit(event: SubmitEvent) {
    event.preventDefault();
    if (from && to) onconnect(from.id, to.id);
  }
</script>

<form class="ask surface" onsubmit={submit} data-testid="ask-card">
  <p class="eyebrow">Ask the oracle</p>
  <h2>How are they related?</h2>
  <div class="pickers">
    <NodePicker {pantheon} label="First figure" placeholder="Choose a figure…" value={from} testid="ask-from" onpick={(node) => (from = node)} />
    <span class="and" aria-hidden="true">&amp;</span>
    <NodePicker {pantheon} label="Second figure" placeholder="…and another" value={to} testid="ask-to" onpick={(node) => (to = node)} />
  </div>
  <button class="button-gold" type="submit" disabled={!from || !to}>Reveal</button>

  {#if examples.length}
    <p class="try">or try</p>
    <ul>
      {#each examples as [a, b] (a.id + b.id)}
        <li>
          <button type="button" onclick={() => onconnect(a.id, b.id)}>{a.label} <span>&amp;</span> {b.label}</button>
        </li>
      {/each}
    </ul>
  {/if}
</form>

<style>
  .ask {
    display: grid;
    gap: 12px;
    padding: 20px;
  }

  h2 {
    margin: -4px 0 2px;
    font: 500 26px/1.15 var(--font-serif);
  }

  .pickers {
    display: grid;
    gap: 6px;
  }

  .and {
    justify-self: center;
    color: var(--gold);
    font: italic 500 20px/1 var(--font-serif);
  }

  .try {
    margin: 4px 0 -4px;
    color: var(--ink-muted);
    font: italic 500 16px/1 var(--font-serif);
  }

  ul {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  ul button {
    padding: 5px 12px;
    border: 1px solid var(--line);
    border-radius: 999px;
    background: rgb(255 255 255 / 0.03);
    font: 600 15px/1.2 var(--font-serif);
  }

  ul button span {
    color: var(--gold);
    font-style: italic;
  }

  ul button:hover {
    border-color: var(--line-strong);
    background: rgb(217 180 90 / 0.08);
  }
</style>
