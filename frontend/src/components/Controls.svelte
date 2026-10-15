<script lang="ts">
  import type { Pantheon } from '../lib/graph';
  import type { AppState } from '../lib/state.svelte';
  import { kindStyle, RELATIONS } from '../lib/theme';

  let { pantheon, app }: { pantheon: Pantheon; app: AppState } = $props();

  const kinds = $derived(pantheon.kinds());
  const relationKinds = $derived(Object.keys(RELATIONS).filter((kind) => pantheon.edges.some((edge) => edge.kind === kind)));
</script>

<div class="controls surface">
  <div class="layouts" role="radiogroup" aria-label="Layout">
    {#each [['constellation', 'Constellation'], ['tree', 'Family tree']] as const as [value, label] (value)}
      <button
        type="button"
        role="radio"
        aria-checked={app.layout === value}
        class:on={app.layout === value}
        onclick={() => (app.layout = value)}>{label}</button
      >
    {/each}
  </div>

  <div class="extra">
    <ul class="legend" aria-label="Legend">
      {#each kinds as [kind, count] (kind)}
        <li><span class="dot" style:--tone={kindStyle(kind).color}></span>{kindStyle(kind).plural} <small>{count}</small></li>
      {/each}
    </ul>

    <div class="relations" aria-label="Relationships shown">
      {#each relationKinds as kind (kind)}
        {@const relation = RELATIONS[kind]!}
        <label>
          <input type="checkbox" checked={!app.hiddenKinds.has(kind)} onchange={() => app.toggleKind(kind)} />
          <span class="line" style:--tone={relation.color} style:--dash={relation.dash}></span>
          {relation.label}
        </label>
      {/each}
    </div>
  </div>
</div>

<style>
  .controls {
    display: grid;
    gap: 14px;
    padding: 14px;
    font-size: 13px;
  }

  .layouts {
    display: grid;
    grid-template-columns: 1fr 1fr;
    padding: 3px;
    border: 1px solid var(--line);
    border-radius: 999px;
    background: rgb(5 7 15 / 0.5);
  }

  .layouts button {
    padding: 7px 12px;
    border: none;
    border-radius: 999px;
    background: none;
    color: var(--ink-soft);
    font: 600 11px/1 var(--font-display);
    letter-spacing: 0.12em;
    text-transform: uppercase;
    white-space: nowrap;
  }

  .layouts button.on {
    background: linear-gradient(180deg, #e9c869, #b8902f);
    color: #1d1505;
  }

  .extra {
    display: grid;
    gap: 12px;
  }

  .legend {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px 14px;
    margin: 0;
    padding: 0;
    list-style: none;
    color: var(--ink-soft);
  }

  .legend li {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .legend small {
    color: var(--ink-muted);
  }

  .dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--tone);
    box-shadow: 0 0 8px var(--tone);
  }

  .relations {
    display: grid;
    gap: 6px;
    padding-top: 12px;
    border-top: 1px solid var(--line);
  }

  .relations label {
    display: flex;
    align-items: center;
    gap: 10px;
    color: var(--ink-soft);
    cursor: pointer;
  }

  .relations input {
    accent-color: var(--gold);
  }

  .line {
    width: 26px;
    border-top: 2px var(--dash) var(--tone);
  }

  @media (max-width: 760px) {
    .controls {
      padding: 4px;
      border-radius: 999px;
    }

    .extra {
      display: none;
    }
  }
</style>
