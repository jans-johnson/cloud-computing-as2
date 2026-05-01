// Thin wrapper around fetch — keeps the per-page JS focused on UI.
// Token is stored in localStorage so the same code works for the
// stateless Lambda backend and the cookie-based Flask backend (the
// server simply ignores the Authorization header when a session
// cookie is present, and vice versa).

const TOKEN_KEY = "music_token";
const USER_KEY = "music_user";

function base() {
  return window.APP_CONFIG.API_BASE.replace(/\/$/, "");
}

function authHeaders() {
  const t = localStorage.getItem(TOKEN_KEY);
  return t ? { Authorization: `Bearer ${t}` } : {};
}

async function request(path, { method = "GET", body } = {}) {
  const res = await fetch(base() + path, {
    method,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  let data = null;
  try { data = await res.json(); } catch { /* empty body */ }
  if (!res.ok) {
    const msg = (data && data.error) || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return data;
}

export const api = {
  async login(email, password) {
    const data = await request("/api/login", { method: "POST", body: { email, password } });
    if (data.token) localStorage.setItem(TOKEN_KEY, data.token);
    localStorage.setItem(USER_KEY, data.user_name);
    return data;
  },
  async register(email, user_name, password) {
    return request("/api/register", { method: "POST", body: { email, user_name, password } });
  },
  async logout() {
    try { await request("/api/logout", { method: "POST" }); } catch { /* ignore */ }
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },
  currentUserName() {
    return localStorage.getItem(USER_KEY);
  },
  searchMusic({ title, artist, album, year }) {
    const params = new URLSearchParams();
    if (title) params.set("title", title);
    if (artist) params.set("artist", artist);
    if (album) params.set("album", album);
    if (year) params.set("year", year);
    return request("/api/music?" + params.toString());
  },
  listSubscriptions() {
    return request("/api/subscriptions");
  },
  subscribe(song) {
    return request("/api/subscriptions", { method: "POST", body: song });
  },
  unsubscribe(song) {
    return request("/api/subscriptions", { method: "DELETE", body: song });
  },
};
