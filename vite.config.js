import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],

  // Relative base so the production build works when dropped into any
  // subfolder — e.g. XAMPP's htdocs/perennia/ — on any port, without
  // rebuilding or editing asset paths.
  base: "./",

  server: {
    port: 5173,
    // Never fail because a port is taken — pick the next free one instead.
    strictPort: false,
    open: false,
    proxy: {
      // During `npm run dev`, forward /api calls to the Python backend
      // (see backend/README / PASS1_NOTES.md) so the same relative-path
      // fetch("api/...") calls work both in dev and in the built app.
      "/api": {
        target: "http://localhost:8001",
        changeOrigin: true,
        // Don't hard-fail dev server startup if the backend isn't running;
        // the client already falls back to bundled content on error.
        configure: (proxy) => {
          proxy.on("error", () => {});
        },
      },
      // Uploaded brand assets (logo, favicon) — served by the backend
      // from backend/data/uploads/, referenced by branding.logo_url /
      // branding.favicon_url as root-relative paths.
      "/uploads": {
        target: "http://localhost:8001",
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on("error", () => {});
        },
      },
    },
  },

  preview: {
    port: 4173,
    strictPort: false,
  },
});
