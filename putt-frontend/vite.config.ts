import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tsconfigPaths from 'vite-tsconfig-paths';

// DG-Putt SPA (Phase 2.5: CRA -> Vite, copied in from the standalone
// puttingLeague repo during the monorepo consolidation).
//
// base: '/' is interim; becomes '/svdgc/putt/' (with a matching React Router
// basename) when path-based routing lands. build.outDir: 'build' preserves the
// existing `npm run build && aws s3 sync build/ s3://<bucket>` deploy.
//
// DG-Putt uses Socket.IO for live bracket/match updates: the client connects to
// API_BASE_URL (the dev-server origin in local dev), so the dev server must
// proxy BOTH the HTTP API (/api) and the Socket.IO transport (/socket.io, with
// ws upgrade) to the backend.
//
// NOTE: API calls still target the standalone DG-Putt paths (/api/tournaments,
// etc.). Repointing them to the consolidated /api/putt/* on api.dg-rater.com is
// a deliberate later (cutover) step, not part of this tooling swap.
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
      '/socket.io': {
        target: 'http://localhost:5000',
        ws: true,
      },
    },
  },
});
