// Re-export the shared API base so ported DG-Dubs components can keep their
// original `../config/api` import unchanged. Single source of truth lives in
// web/src/config/api.ts.
export { API_BASE_URL } from '../../../config/api';
