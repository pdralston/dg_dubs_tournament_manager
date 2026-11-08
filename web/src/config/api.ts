// Backend origin for both the HTTP API (/api/*) and the Socket.IO transport.
// Set VITE_API_URL at build time (see .env.example); falls back to the local
// backend for development (the dev server also proxies /api and /socket.io).
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';
