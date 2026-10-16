<script lang="ts">
  import { initial, kindStyle } from '../lib/theme';
  import type { NodeData } from '../lib/types';

  let { node, size = 40 }: { node: NodeData; size?: number } = $props();
</script>

<span class="medallion" style:--size="{size}px" style:--tone={kindStyle(node.kind).color} aria-hidden="true"
  >{initial(node)}</span
>

<style>
  .medallion {
    display: inline-grid;
    flex-shrink: 0;
    place-items: center;
    width: var(--size);
    height: var(--size);
    border-radius: 50%;
    background: var(--tone);
    color: #fff;
    font: 600 calc(var(--size) * 0.5) / 1 var(--font-serif);
    user-select: none;
  }
</style>
