import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      manifest: {
        name: "forkOS",
        short_name: "forkOS",
        start_url: "/",
        display: "standalone",
        background_color: "#0b0b0c",
        theme_color: "#0b0b0c",
      },
      workbox: {
        runtimeCaching: [
          {
            // OFFLINE = SADECE OKUMA. Mutation'lar cache'lenmez.
            urlPattern: ({ url, request }) =>
              url.pathname.startsWith("/api/") && request.method === "GET",
            handler: "StaleWhileRevalidate",
            options: {
              cacheName: "lifeos-api",
              expiration: { maxEntries: 200, maxAgeSeconds: 60 * 60 * 24 * 7 },
            },
          },
        ],
      },
    }),
  ],
  server: {
    // Compose icinde API_TARGET=http://api:8787 gelir; disarida npm run dev
    // ile calistirinca 127.0.0.1'e duser.
    proxy: { "/api": process.env.API_TARGET ?? "http://127.0.0.1:8787" },
  },
});
