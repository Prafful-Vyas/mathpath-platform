/// <reference types="vitest" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Dev proxy to the two services; in docker-compose nginx does the same routing.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api/content": { target: "http://127.0.0.1:5001", rewrite: (p) => p.replace(/^\/api\/content/, "") },
      "/api/practice": { target: "http://127.0.0.1:8000", rewrite: (p) => p.replace(/^\/api\/practice/, "") },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
  },
});
