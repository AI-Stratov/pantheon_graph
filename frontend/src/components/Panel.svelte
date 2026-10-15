<script lang="ts">
  import type { Snippet } from 'svelte';

  interface Props {
    onclose: () => void;
    children: Snippet;
    /** Size of the area the panel covers, so the canvas can keep its focus visible. */
    covered?: { right: number; bottom: number };
  }

  let { onclose, children, covered = $bindable({ right: 0, bottom: 0 }) }: Props = $props();

  let width = $state(0);
  let height = $state(0);
  let expanded = $state(false);
  const mobile = window.matchMedia('(max-width: 760px)');
  let isMobile = $state(mobile.matches);
  mobile.addEventListener('change', (event) => (isMobile = event.matches));

  $effect(() => {
    covered = isMobile ? { right: 0, bottom: height } : { right: width + 24, bottom: 0 };
  });
</script>

<aside
  class="panel surface"
  class:expanded
  bind:clientWidth={width}
  bind:clientHeight={height}
  aria-label="Details"
>
  <button class="handle" type="button" aria-label={expanded ? 'Collapse' : 'Expand'} onclick={() => (expanded = !expanded)}>
    <span></span>
  </button>
  <button class="close" type="button" aria-label="Close" onclick={onclose}>×</button>
  <div class="content">
    {@render children()}
  </div>
</aside>

<style>
  .panel {
    position: absolute;
    z-index: 20;
    top: 16px;
    right: 16px;
    bottom: 16px;
    display: flex;
    flex-direction: column;
    width: min(420px, calc(100vw - 32px));
    overflow: hidden;
    animation: slide-in 0.35s var(--ease) both;
  }

  .content {
    flex: 1;
    overflow-y: auto;
    padding: 28px 26px 32px;
    overscroll-behavior: contain;
    scrollbar-color: var(--night-600) transparent;
  }

  .close {
    position: absolute;
    z-index: 1;
    top: 12px;
    right: 12px;
    width: 34px;
    height: 34px;
    border: 1px solid var(--line);
    border-radius: 50%;
    background: rgb(5 7 15 / 0.5);
    color: var(--ink-soft);
    font-size: 20px;
    line-height: 1;
  }

  .close:hover {
    border-color: var(--line-strong);
    color: var(--ink);
  }

  .handle {
    display: none;
  }

  @keyframes slide-in {
    from {
      opacity: 0;
      transform: translateX(24px);
    }
  }

  @media (max-width: 760px) {
    .panel {
      top: auto;
      right: 0;
      bottom: 0;
      left: 0;
      width: 100%;
      max-height: 58dvh;
      border-radius: var(--radius) var(--radius) 0 0;
      border-bottom: none;
      animation-name: sheet-in;
      transition: max-height 0.3s var(--ease);
    }

    .panel.expanded {
      max-height: 88dvh;
    }

    .handle {
      display: grid;
      place-items: center;
      height: 22px;
      border: none;
      background: none;
    }

    .handle span {
      width: 42px;
      height: 4px;
      border-radius: 2px;
      background: var(--night-600);
    }

    .content {
      padding: 4px 20px calc(24px + env(safe-area-inset-bottom));
    }

    @keyframes sheet-in {
      from {
        transform: translateY(40%);
        opacity: 0;
      }
    }
  }
</style>
