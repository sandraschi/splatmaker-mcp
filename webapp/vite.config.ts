import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 11092,
    proxy: {
      "/api": "http://localhost:11091",
      "/mcp": "http://localhost:11091",
    },
  },
});
