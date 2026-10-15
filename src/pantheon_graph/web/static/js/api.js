const config = window.PANTHEON_CONFIG ?? {};
const BASE = (config.apiBase ?? '').replace(/\/$/, '');

/** True for the static demo build: data comes from a JSON snapshot, not the API. */
export const isSnapshot = Boolean(config.snapshot);

export class ApiError extends Error {}

async function request(url, init = {}) {
  const response = await fetch(url, {
    ...init,
    headers: { Accept: 'application/json', ...init.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = typeof body.detail === 'string' ? body.detail : response.statusText;
    throw new ApiError(`${response.status} ${detail}`);
  }
  return response.json();
}

export const api = {
  graph: () => request(isSnapshot ? config.snapshot : `${BASE}/api/graph`),
  refresh: () => request(`${BASE}/api/graph/refresh`, { method: 'POST' }),
};
