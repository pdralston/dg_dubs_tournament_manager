// API base URL (also used as the Socket.IO connection origin — see
// hooks/useWebSocket.ts). Set VITE_API_URL at build time (see .env.example);
// falls back to the local backend for development.
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

export { API_BASE_URL };
