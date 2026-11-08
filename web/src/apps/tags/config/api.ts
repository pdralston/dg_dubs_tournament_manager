// Re-export the shared API base so the ported DG-Tags services client can keep
// its original `../config/api` import unchanged. Single source of truth lives
// in web/src/config/api.ts.
export { API_BASE_URL } from '../../../config/api';
