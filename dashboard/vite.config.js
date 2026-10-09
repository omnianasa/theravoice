import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiTarget = process.env.THERAVOICE_API_URL || "http://127.0.0.1:8000";

export default defineConfig(({ command }) => ({
  base: process.env.VITE_BASE_PATH || (command === "build" ? "/dashboard/" : "/"),
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./src/testSetup.js"],
    clearMocks: true,
  },
  server: {
    proxy: {
      "/api/v1": apiTarget,
    },
  },
}));
