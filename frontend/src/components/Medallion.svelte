<script lang="ts">
  import { initial, kindStyle } from '../lib/theme';
  import type { NodeData } from '../lib/types';

  let { node, size = 40 }: { node: NodeData; size?: number } = $props();
  const style = $derived(kindStyle(node.kind));
</script>

<span
  class="medallion"
  style:--size="{size}px"
  style:--tone={style.color}
  style:--shade={style.shade}
  aria-hidden="true">{initial(node)}</span
>

<style>
  .medallion {
    display: inline-grid;
    flex-shrink: 0;
    place-items: center;
    width: var(--size);
    height: var(--size);
    border: max(1.5px, calc(var(--size) * 0.045)) solid var(--tone);
    border-radius: 50%;
    background: radial-gradient(circle at 50% 30%, var(--tone), var(--shade) 58%, #05070f);
    box-shadow:
      inset 0 0 0 calc(var(--size) * 0.08) rgb(5 7 15 / 0.35),
      0 0 calc(var(--size) * 0.45) color-mix(in srgb, var(--tone) 30%, transparent);
    color: #fff8e6;
    font: 600 calc(var(--size) * 0.46) / 1 var(--font-serif);
    text-shadow: 0 1px 2px rgb(0 0 0 / 0.5);
    user-select: none;
  }
</style>
