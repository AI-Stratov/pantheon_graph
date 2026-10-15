import type { GraphData } from './types';

interface RuntimeConfig {
  apiBase?: string;
  /** Static demo build: path of a graph.json snapshot to read instead of the API. */
  snapshot?: string | null;
}

declare global {
  interface Window {
    PANTHEON_CONFIG?: RuntimeConfig;
  }
}

const config: RuntimeConfig = window.PANTHEON_CONFIG ?? {};

export async function loadGraph(signal?: AbortSignal): Promise<GraphData> {
  const url = config.snapshot ?? `${(config.apiBase ?? '').replace(/\/$/, '')}/api/graph`;
  const response = await fetch(url, { headers: { Accept: 'application/json' }, signal });
  if (!response.ok) throw new Error(`Could not load the pantheon (${response.status} ${response.statusText})`);
  return (await response.json()) as GraphData;
}
