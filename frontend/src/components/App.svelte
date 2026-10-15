<script lang="ts">
  import { onMount } from 'svelte';

  import { loadGraph } from '../lib/api';
  import { Pantheon } from '../lib/graph';
  import { AppState } from '../lib/state.svelte';
  import type { Insets } from '../lib/types';
  import AskCard from './AskCard.svelte';
  import ConnectionCard from './ConnectionCard.svelte';
  import Controls from './Controls.svelte';
  import DeityCard from './DeityCard.svelte';
  import NodePicker from './NodePicker.svelte';
  import Panel from './Panel.svelte';

  const app = new AppState();
  let pantheon = $state.raw<Pantheon | null>(null);
  let error = $state<string | null>(null);
  let askOpen = $state(false);

  const mobileQuery = window.matchMedia('(max-width: 760px)');
  let mobile = $state(mobileQuery.matches);
  mobileQuery.addEventListener('change', (event) => (mobile = event.matches));

  // Geometry of the floating UI, so the camera frames what is actually visible
  let sideWidth = $state(0);
  let headerHeight = $state(0);
  let dockHeight = $state(0);
  let covered = $state({ right: 0, bottom: 0 });

  const selection = $derived(app.selection);
  const path = $derived(
    pantheon && selection?.kind === 'path' ? pantheon.path(selection.from, selection.to, app.hiddenKinds) : null,
  );
  const panelOpen = $derived(selection !== null || (mobile && askOpen));
  const insets: Insets = $derived(
    mobile
      ? { top: headerHeight + 12, right: 0, bottom: panelOpen ? covered.bottom : dockHeight + 16, left: 0 }
      : { top: 0, right: panelOpen ? covered.right : 0, bottom: 0, left: sideWidth + 24 },
  );

  onMount(() => {
    const controller = new AbortController();
    loadGraph(controller.signal)
      .then((data) => {
        const loaded = new Pantheon(data);
        app.fromQuery(location.search, (id) => loaded.has(id));
        pantheon = loaded;
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) error = reason instanceof Error ? reason.message : String(reason);
      });
    return () => controller.abort();
  });

  // Every view is a shareable link
  $effect(() => {
    if (!pantheon) return;
    const query = app.toQuery();
    if (query !== location.search) history.replaceState(null, '', `${location.pathname}${query}`);
  });

  function select(id: string) {
    askOpen = false;
    app.select(id);
  }

  function connect(from: string, to: string) {
    askOpen = false;
    app.connect(from, to);
  }

  function close() {
    askOpen = false;
    app.clear();
  }

  function onkeydown(event: KeyboardEvent) {
    const typing = event.target instanceof HTMLInputElement;
    if (event.key === 'Escape' && !typing) close();
    if (event.key === '/' && !typing) {
      event.preventDefault();
      document.querySelector<HTMLInputElement>('[data-testid="search"]')?.focus();
    }
  }
</script>

<svelte:window {onkeydown} />

<main class="app">
  {#if pantheon}
    <!-- Cytoscape is most of the bundle: load it in parallel with the rest of the UI -->
    {#await import('./GraphCanvas.svelte') then { default: GraphCanvas }}
      <GraphCanvas {pantheon} {app} {path} {insets} onselect={select} onclear={close} />
    {/await}

    <div class="side" bind:clientWidth={sideWidth}>
      <header class="brand" bind:clientHeight={headerHeight}>
        <h1>Pantheon</h1>
        <p>The family of the Greek gods</p>
        <div class="search">
          <NodePicker
            {pantheon}
            label="Search the pantheon"
            placeholder="Find a god, titan or hero…"
            clearOnPick
            testid="search"
            onpick={(node) => select(node.id)}
          />
        </div>
      </header>
      {#if !mobile}
        <AskCard {pantheon} onconnect={connect} />
      {/if}
    </div>

    <div class="dock" bind:clientHeight={dockHeight} class:hidden={mobile && panelOpen}>
      {#if mobile}
        <button class="button-gold oracle" type="button" onclick={() => (askOpen = true)}>How are they related?</button>
      {/if}
      <Controls {pantheon} {app} />
    </div>

    {#if panelOpen}
      <Panel onclose={close} bind:covered>
        {#if selection?.kind === 'node'}
          {#key selection.id}
            <DeityCard {pantheon} node={pantheon.node(selection.id)} onselect={select} onconnect={connect} />
          {/key}
        {:else if selection?.kind === 'path'}
          <ConnectionCard
            {pantheon}
            from={pantheon.node(selection.from)}
            to={pantheon.node(selection.to)}
            {path}
            filtered={app.hiddenKinds.size > 0}
            onselect={select}
            onswap={() => connect(selection.to, selection.from)}
          />
        {:else}
          <AskCard {pantheon} onconnect={connect} />
        {/if}
      </Panel>
    {/if}
  {:else if error}
    <div class="splash" role="alert">
      <h1>Pantheon</h1>
      <p>{error}</p>
      <button class="button-gold" type="button" onclick={() => location.reload()}>Try again</button>
    </div>
  {:else}
    <div class="splash" aria-busy="true">
      <h1>Pantheon</h1>
      <p>Summoning the gods…</p>
    </div>
  {/if}
</main>

<style>
  .app {
    position: relative;
    height: 100%;
    overflow: hidden;
  }

  .side {
    position: absolute;
    z-index: 10;
    top: 20px;
    left: 20px;
    display: grid;
    gap: 16px;
    width: 340px;
    pointer-events: none;
  }

  .side > :global(*) {
    pointer-events: auto;
  }

  .brand h1 {
    margin: 0;
    color: var(--gold-bright);
    font: 700 34px/1 var(--font-display);
    letter-spacing: 0.32em;
    text-transform: uppercase;
    text-shadow: 0 0 24px rgb(217 180 90 / 0.35);
  }

  .brand p {
    margin: 6px 0 14px;
    color: var(--ink-soft);
    font: italic 500 19px/1.2 var(--font-serif);
  }

  .dock {
    position: absolute;
    z-index: 10;
    bottom: 20px;
    left: 20px;
    width: 340px;
  }

  .splash {
    display: grid;
    place-content: center;
    gap: 6px;
    height: 100%;
    text-align: center;
  }

  .splash h1 {
    margin: 0;
    color: var(--gold-bright);
    font: 700 40px/1 var(--font-display);
    letter-spacing: 0.32em;
    text-transform: uppercase;
  }

  .splash p {
    color: var(--ink-soft);
    font: italic 500 20px/1.3 var(--font-serif);
  }

  .splash[aria-busy='true'] p {
    animation: breathe 1.6s ease-in-out infinite;
  }

  @keyframes breathe {
    50% {
      opacity: 0.4;
    }
  }

  @media (max-width: 760px) {
    .side {
      top: 0;
      right: 0;
      left: 0;
      width: auto;
      padding: calc(12px + env(safe-area-inset-top)) 16px 12px;
      background: linear-gradient(rgb(5 7 15 / 0.92), rgb(5 7 15 / 0.75) 70%, transparent);
    }

    .brand h1 {
      font-size: 22px;
    }

    .brand p {
      margin: 2px 0 10px;
      font-size: 16px;
    }

    .dock {
      right: 16px;
      bottom: calc(16px + env(safe-area-inset-bottom));
      left: 16px;
      display: grid;
      gap: 10px;
      width: auto;
    }

    .dock.hidden {
      display: none;
    }

    .oracle {
      padding: 14px;
      font-size: 13px;
    }
  }
</style>
