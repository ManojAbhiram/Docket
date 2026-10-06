import path from "node:path";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Vite build and dev server. Test settings live in vitest.config.ts.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": path.resolve(import.meta.dirname, "src") },
  },
  server: {
    port: 5173,
    strictPort: true,
    // The browser talks to one origin (ADR-0004, ADR-0006): the dev server forwards the API.
    proxy: {
      "/api": { target: process.env.API_PROXY_TARGET ?? "http://localhost:8080" },
      "/healthz": { target: process.env.API_PROXY_TARGET ?? "http://localhost:8080" },
    },
  },
  preview: { port: 4173, strictPort: true },
  build: {
    sourcemap: true,
    // A chunk over this size is a review question, not a warning to silence.
    chunkSizeWarningLimit: 500,
  },
});
