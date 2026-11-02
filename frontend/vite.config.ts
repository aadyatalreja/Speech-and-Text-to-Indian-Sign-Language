import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { configureClientIp } from "./src/services/devProxy";
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": {
    target: process.env.BACKEND_URL ?? "http://localhost:8000", ws: true,
    configure: configureClientIp,
  }, "/generated": process.env.BACKEND_URL ?? "http://localhost:8000", "/signs": process.env.BACKEND_URL ?? "http://localhost:8000" } },
});
