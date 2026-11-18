import axios from "axios";

/*
  Frontend runs behind Caddy:
    - frontend: /
    - backend:  /api/*
  So we use SAME-ORIGIN and call "/api/..." paths directly.
*/

export const API_BASE = "/api";
export const API = API_BASE;

export function apiUrl(path) {
  if (!path.startsWith("/")) path = "/" + path;
  if (path.startsWith("/api/")) return path;
  return `${API_BASE}${path}`;
}

const api = axios.create({
  baseURL: API_BASE,
});

api.interceptors.request.use((config) => {
  // Prefer the current session saved by the auth store. A legacy "token" key
  // left over from older versions of the app must never override it.
  let token = null;
  try {
    const raw = localStorage.getItem("auth-storage");
    if (raw) {
      const parsed = JSON.parse(raw);
      token = parsed?.state?.token || null;
    }
  } catch (e) {
    // ignore malformed localStorage
  }
  if (!token) {
    token = localStorage.getItem("token");
  }

  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;
