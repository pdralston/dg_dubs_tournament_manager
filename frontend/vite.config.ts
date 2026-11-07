import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tsconfigPaths from 'vite-tsconfig-paths';

// DG-Dubs SPA (Phase 2.5 pilot: CRA -> Vite).
//
// base: '/' is the interim setting — the app is still served at the dg-rater.com
// root during the transition. When path-based routing lands, this becomes
// '/svdgc/dubs/' with a matching React Router basename.
//
// build.outDir: 'build' preserves the existing deploy path so the documented
// `npm run build && aws s3 sync build/ s3://<bucket>` workflow is unchanged
// (Vite's default is 'dist').
export default defineConfig({
  plugins: [react(), tsconfigPaths()],
  base: '/',
  build: {
    outDir: 'build',
  },
  server: {
    port: 3000,
    // Proxy API calls to the local backend during development so the SPA can
    // use a relative/omitted base. Harmless when VITE_API_URL points elsewhere.
    proxy: {
      '/api': 'http://localhost:5000',
    },
  },
});
