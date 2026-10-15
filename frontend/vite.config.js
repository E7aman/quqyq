import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Сборка отдаётся Django из /static/, в dev — прокси на бэкенд :8000
export default defineConfig({
  base: "/static/",
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": "http://localhost:8000", "/ws": { target: "ws://localhost:8000", ws: true } },
  },
});
