const BASE = (window.PANTHEON_API_BASE ?? '').replace(/\/$/, '');

export class ApiError extends Error {}

async function request(path, init = {}) {
  const response = await fetch(`${BASE}${path}`, {
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
  graph: () => request('/api/graph'),
  refresh: () => request('/api/graph/refresh', { method: 'POST' }),
};
