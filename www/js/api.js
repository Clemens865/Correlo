/**
 * api.js — Communication layer for the API Correlation Explorer.
 * Talks to the Python backend for data fetching and AI calls.
 */

const BASE = '';  // same origin

/** Fetch the curated API catalog + locations from the server. */
export async function fetchCatalog() {
  const r = await fetch(`${BASE}/api/catalog`);
  if (!r.ok) throw new Error(`Catalog fetch failed: ${r.status}`);
  return r.json();  // { apis: [...], locations: [...] }
}

/** Fetch a dataset by catalog ID. */
export async function fetchDataset(id, { lat = 48.21, lon = 16.37, days = 30, country = 'WLD' } = {}) {
  const r = await fetch(`${BASE}/api/fetch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id, lat, lon, days, country }),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.error || `Fetch failed: ${r.status}`);
  }
  return r.json();  // { labels, values, id, name, unit, category, count }
}

/** Proxy-fetch any URL (solves CORS). */
export async function proxyFetch(url, authHeader) {
  const headers = {};
  if (authHeader) headers['X-Api-Auth'] = authHeader;
  const r = await fetch(`${BASE}/api/proxy?url=${encodeURIComponent(url)}`, { headers });
  if (!r.ok) throw new Error(`Proxy fetch failed: ${r.status}`);
  return r.json();
}

/** AI: parse arbitrary JSON to detect data fields. */
export async function aiParse(data, url) {
  const r = await fetch(`${BASE}/api/ai/parse`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ data, url }),
  });
  if (!r.ok) throw new Error(`AI parse failed: ${r.status}`);
  return r.json();
}

/** AI: discover APIs for a natural language query. */
export async function aiDiscover(query) {
  const r = await fetch(`${BASE}/api/ai/discover`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  });
  if (!r.ok) throw new Error(`AI discover failed: ${r.status}`);
  return r.json();
}

/** AI: get insight on correlation results. */
export async function aiInsight({ nameA, unitA, nameB, unitB, pearson, spearman, r_squared, n, period }) {
  const r = await fetch(`${BASE}/api/ai/insight`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nameA, unitA, nameB, unitB, pearson, spearman, r_squared, n, period }),
  });
  if (!r.ok) throw new Error(`AI insight failed: ${r.status}`);
  return r.json();  // { insight: "..." }
}
