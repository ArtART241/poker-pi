import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

const api = "http://localhost:8000";

export default defineConfig({
  plugins: [svelte()],
  server: {
    fs: { allow: [".."] }, // the docs live in ../docs
    proxy: {
      "/api": { target: api, changeOrigin: true },
      "/docs": { target: api, changeOrigin: true },
      "/openapi.json": { target: api, changeOrigin: true },
      "/openapi.yaml": { target: api, changeOrigin: true },
    },
  },
});
