<script lang="ts">
  import type { Pantheon, Path } from '../lib/graph';
  import { describeStep, kinship } from '../lib/kinship';
  import { kindStyle } from '../lib/theme';
  import { text, type NodeData } from '../lib/types';
  import Medallion from './Medallion.svelte';

  interface Props {
    pantheon: Pantheon;
    from: NodeData;
    to: NodeData;
    path: Path | null;
    filtered: boolean;
    onselect: (id: string) => void;
    onswap: () => void;
  }

  let { pantheon, from, to, path, filtered, onselect, onswap }: Props = $props();

  const story = $derived(path ? kinship(path, pantheon) : null);
  const listFormat = new Intl.ListFormat('en', { type: 'conjunction' });
  const steps = $derived(path ? path.edges.length : 0);
</script>

<article class="connection" data-testid="connection-card">
  <p class="eyebrow">Connection</p>

  {#if story}
    <h2 class="sentence" data-testid="kinship">
      {#if story.relation}
        <em>{from.label}</em> is the <strong>{story.relation}</strong> of <em>{to.label}</em>
      {:else}
        <em>{from.label}</em> and <em>{to.label}</em> are linked through {listFormat.format(story.via.map((node) => node.label))}
      {/if}
    </h2>
    <p class="meta">
      {steps} {steps === 1 ? 'step' : 'steps'} apart
      <button type="button" class="swap" onclick={onswap}>⇅ Reverse</button>
    </p>

    <ol class="timeline">
      {#each path!.nodes as node, index (node.id)}
        {@const edge = path!.edges[index]}
        <li class="person">
          <button type="button" onclick={() => onselect(node.id)}>
            <Medallion {node} size={44} />
            <span class="who">
              <strong>{node.label}</strong>
              <small>{kindStyle(node.kind).label}{text(node, 'domain') ? ` · ${text(node, 'domain')}` : ''}</small>
            </span>
          </button>
        </li>
        {#if edge}
          <li class="link"><span>{describeStep(edge, node)}</span></li>
        {/if}
      {/each}
    </ol>
  {:else}
    <h2 class="sentence">
      <em>{from.label}</em> and <em>{to.label}</em> are not related
    </h2>
    <p class="meta">
      {filtered
        ? 'Not with the relationships you have hidden. Show them again to search further.'
        : 'They come from separate lineages of the myths.'}
    </p>
  {/if}
</article>

<style>
  .sentence {
    margin: 8px 30px 6px 0;
    font: 500 27px/1.2 var(--font-serif);
  }

  .sentence em {
    font-style: normal;
    font-weight: 700;
  }

  .sentence strong {
    color: var(--sky);
    font-style: italic;
    font-weight: 600;
  }

  .meta {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 0 0 20px;
    color: var(--ink-muted);
    font-size: 14px;
  }

  .swap {
    padding: 3px 10px;
    border: 1px solid var(--line-strong);
    border-radius: 999px;
    background: var(--surface);
    color: var(--ink-soft);
    font-size: 12px;
  }

  .swap:hover {
    background: var(--surface-sunk);
  }

  .timeline {
    position: relative;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  /* The thread running through the medallions */
  .timeline::before {
    content: '';
    position: absolute;
    top: 24px;
    bottom: 24px;
    left: 25px;
    width: 2px;
    background: var(--line-strong);
  }

  .timeline li {
    position: relative;
  }

  .person button {
    display: flex;
    gap: 14px;
    align-items: center;
    width: 100%;
    padding: 4px;
    border: none;
    border-radius: 999px 12px 12px 999px;
    background: none;
    text-align: left;
  }

  .person button:hover {
    background: var(--surface-sunk);
  }

  .who {
    display: grid;
  }

  .who strong {
    font: 700 20px/1.1 var(--font-serif);
  }

  .who small {
    color: var(--ink-muted);
    font-size: 12.5px;
  }

  .link {
    padding: 7px 0 7px 64px;
  }

  .link span {
    color: var(--sky);
    font: italic 600 16px/1.2 var(--font-serif);
  }
</style>
