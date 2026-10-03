import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiTarget = process.env.THERAVOICE_API_URL || "http://127.0.0.1:8000";

export default defineConfig(({ command }) => ({
  base: command === "build" ? "/dashboard/" : "/",
  plugins: [react()],
  server: {
    proxy: {
      "/auth": apiTarget,
      "/health": apiTarget,
      "/ingestion": apiTarget,
      "/patients": apiTarget,
    },
  },
}));