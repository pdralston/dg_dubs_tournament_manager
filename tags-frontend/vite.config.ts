import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tsconfigPaths from 'vite-tsconfig-paths';

// DG-Tags SPA (Phase 2.5: CRA -> Vite).
//
// base: '/' is interim; becomes '/svdgc/tags/' (with a matching React Router
// basename) when path-based routing lands. build.outDir: 'build' preserves the
// documented `npm run build && aws s3 sync build/ s3://<bucket>` deploy.
export default defineConfig({
  plugins: [react(), tsconfigPaths()],
  base: '/',
  build: {
    outDir: 'build',
  },
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://localhost:5000',
    },
  },
});
