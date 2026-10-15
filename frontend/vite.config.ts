import { svelte } from '@sveltejs/vite-plugin-svelte';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [svelte()],
  // Relative asset URLs: the same build works at / (FastAPI) and under /pantheon_graph/ (Pages)
  base: './',
  build: {
    outDir: '../src/pantheon_graph/web/dist',
    emptyOutDir: true,
    target: 'es2023',
    // The lazily loaded graph chunk is mostly Cytoscape itself
    chunkSizeWarningLimit: 600,
  },
  server: {
    proxy: { '/api': 'http://127.0.0.1:8080' },
  },
  test: {
    include: ['src/**/*.test.ts'],
  },
});
