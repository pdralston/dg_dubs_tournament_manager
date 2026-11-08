// Re-export the shared API base so the ported DG-Putt components and the
// useWebSocket hook keep their original `../config/api` import unchanged. This
// is also the Socket.IO connection origin (see hooks/useWebSocket.ts). Single
// source of truth lives in web/src/config/api.ts.
export { API_BASE_URL } from '../../../config/api';
