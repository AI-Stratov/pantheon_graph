<script lang="ts">
  import type { Pantheon } from '../lib/graph';
  import { kindStyle } from '../lib/theme';
  import { list, text, type NodeData } from '../lib/types';
  import Medallion from './Medallion.svelte';
  import NodePicker from './NodePicker.svelte';

  interface Props {
    pantheon: Pantheon;
    node: NodeData;
    onselect: (id: string) => void;
    onconnect: (from: string, to: string) => void;
  }

  let { pantheon, node, onselect, onconnect }: Props = $props();

  const style = $derived(kindStyle(node.kind));
  const relatives = $derived(pantheon.relatives(node.id));
  const groups = $derived(
    [
      ['Parents', relatives.parents],
      ['Consorts', relatives.spouses],
      ['Siblings', relatives.siblings],
      ['Children', relatives.children],
    ] as const,
  );
  const symbols = $derived(list(node, 'symbols'));
  const sources = $derived(list(node, 'sources'));
</script>

<article class="deity" data-testid="deity-card">
  <header>
    <Medallion {node} size={76} />
    <div>
      <p class="eyebrow">{style.label}</p>
      <h2>{node.label}</h2>
      {#if text(node, 'greek')}<p class="greek" lang="grc">{text(node, 'greek')}</p>{/if}
    </div>
  </header>

  {#if text(node, 'description')}
    <p class="description">{text(node, 'description')}</p>
  {/if}

  <dl class="facts">
    {#if text(node, 'domain')}<dt>Domain</dt><dd>{text(node, 'domain')}</dd>{/if}
    {#if text(node, 'roman')}<dt>Roman</dt><dd>{text(node, 'roman')}</dd>{/if}
    {#if symbols.length}<dt>Symbols</dt><dd>{symbols.join(', ')}</dd>{/if}
  </dl>

  {#each groups as [title, people] (title)}
    {#if people.length}
      <section>
        <h3>{title} <span>{people.length}</span></h3>
        <ul class="people">
          {#each people as person (person.id)}
            <li>
              <button class="chip" type="button" onclick={() => onselect(person.id)}>
                <Medallion node={person} size={26} />
                {person.label}
              </button>
            </li>
          {/each}
        </ul>
      </section>
    {/if}
  {/each}

  <section class="ask">
    <h3>How is {node.label} related to…</h3>
    <NodePicker
      {pantheon}
      label="Another figure"
      placeholder="another god, titan or hero"
      clearOnPick
      testid="relate-to"
      onpick={(other) => onconnect(node.id, other.id)}
    />
  </section>

  <footer>
    {#if text(node, 'wikipedia')}<a href={text(node, 'wikipedia')} target="_blank" rel="noopener noreferrer">Wikipedia ↗</a>{/if}
    {#if text(node, 'wikidata')}<a href={text(node, 'wikidata')} target="_blank" rel="noopener noreferrer">Wikidata ↗</a>{/if}
    {#if sources.length}<span>Sources: {sources.join(', ')}</span>{/if}
  </footer>
</article>

<style>
  header {
    display: flex;
    gap: 16px;
    align-items: center;
    padding-right: 30px;
  }

  h2 {
    margin: 2px 0 0;
    font: 700 32px/1.05 var(--font-serif);
  }

  .greek {
    margin: 2px 0 0;
    color: var(--ink-soft);
    font: italic 500 20px/1.2 var(--font-serif);
  }

  .description {
    margin: 20px 0 16px;
    font: 500 19px/1.45 var(--font-serif);
  }

  .facts {
    display: grid;
    grid-template-columns: max-content 1fr;
    gap: 6px 16px;
    margin: 0 0 8px;
    font-size: 14px;
  }

  dt {
    color: var(--ink-muted);
  }

  dd {
    margin: 0;
    color: var(--ink-soft);
  }

  section {
    margin-top: 22px;
  }

  h3 {
    margin: 0 0 10px;
    color: var(--ink-muted);
    font: 600 11px/1 var(--font-ui);
    letter-spacing: 0.14em;
    text-transform: uppercase;
  }

  h3 span {
    letter-spacing: 0;
  }

  .people {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .people .chip {
    font: 700 16px/1 var(--font-serif);
  }

  .ask h3 {
    letter-spacing: 0;
    text-transform: none;
    font-size: 13px;
  }

  footer {
    display: flex;
    flex-wrap: wrap;
    gap: 6px 18px;
    margin-top: 26px;
    padding-top: 14px;
    border-top: 1px solid var(--line);
    color: var(--ink-muted);
    font-size: 13px;
  }
</style>
