// API base URL. Set VITE_API_URL at build time (see .env.example); falls back
// to the local backend for development.
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';
