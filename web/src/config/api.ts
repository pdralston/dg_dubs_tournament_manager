// Backend origin for both the HTTP API (/api/*) and the Socket.IO transport.
// Set VITE_API_URL at build time (see .env.example) for production — Vite
// inlines it (e.g. https://api.dg-rater.com).
//
// In dev it is left EMPTY on purpose: an empty base makes fetch('/api/...')
// and io('') hit the *current page origin*, which the Vite dev server proxies
// to the backend (see vite.config.ts: /api and /socket.io). This keeps the API
// same-origin with the page, so the Flask session cookie is first-party and is
// sent back on follow-up requests regardless of whether the page is loaded via
// http://localhost:3000 or http://127.0.0.1:3000. An absolute dev origin (e.g.
// http://localhost:5000) would make the call cross-site from a 127.0.0.1 page,
// and the SameSite=Lax session cookie would be dropped — login would appear to
// succeed (POST /api/auth/login 200) but GET /api/auth/me would run session-less.
export const API_BASE_URL = import.meta.env.VITE_API_URL || '';
