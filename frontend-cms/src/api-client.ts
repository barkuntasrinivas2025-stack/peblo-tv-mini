// Shared shape — copy this file into frontend-viewer/src/ too (or lift into
// a small shared package if you have time) so both apps agree on the
// backend contract instead of duplicating types by hand.

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

let authToken: string | null = null;
export function setAuthToken(token: string) {
  authToken = token;
}

async function request(path: string, options: RequestInit = {}) {
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (authToken) headers["Authorization"] = `Bearer ${authToken}`;
  if (!(options.body instanceof FormData) && options.body) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  login: (username: string, password: string) => {
    const form = new URLSearchParams({ username, password });
    return fetch(`${BASE_URL}/auth/login`, { method: "POST", body: form })
      .then((r) => r.json());
  },
  listShows: (params?: { q?: string; section?: string }) =>
    request(`/admin/shows?${new URLSearchParams(params as any)}`),
  createShow: (payload: object) =>
    request("/admin/shows", { method: "POST", body: JSON.stringify(payload) }),
  validationReport: () => request("/admin/validation-report"),
  publish: () => request("/admin/catalog/publish", { method: "POST" }),
  publishRuns: () => request("/admin/catalog/publish-runs"),
  uploadArtwork: (form: FormData) =>
    request("/admin/artwork", { method: "POST", body: form }),
  // --- viewer-facing (no auth needed) ---
  getCatalog: () => request("/catalog"),
  search: (params: Record<string, string>) =>
    request(`/catalog/search?${new URLSearchParams(params)}`),
};
