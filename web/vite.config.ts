import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tsconfigPaths from 'vite-tsconfig-paths';
import scopeAppCss from './postcss-scope-app.mjs';

// Unified DG-Rater SPA (single-SPA end state). One build, one bucket, one
// CloudFront distribution. Client-side routing over /:org/:app/*.
//
// base: '/' — the app owns the whole origin. In production, CloudFront serves
// this app's index.html for every non-/api, non-/socket.io path (SPA fallback),
// and the client router renders the right org/app from the URL.
//
// Dev proxy forwards the data plane to the backend: HTTP /api and the Socket.IO
// transport /socket.io (ws upgrade, used by DG-Putt live bracket updates).
export default defineConfig({
  plugins: [react(), tsconfigPaths()],
  base: '/',
  css: {
    // Scope each app's CSS under its [data-app="<app>"] host so the three
    // ported apps (which reuse class names + :root var names) don't collide in
    // the single DOM. See postcss-scope-app.mjs.
    postcss: {
      plugins: [scopeAppCss()],
    },
  },
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
