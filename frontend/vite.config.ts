import { fileURLToPath, URL } from "node:url";
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
        background_color: "#FBFAF7",
        theme_color: "#FBFAF7",
      },
      workbox: {
        runtimeCaching: [
          {
            // OFFLINE = SADECE OKUMA. Mutation'lar cache'lenmez.
            urlPattern: ({ url, request }) => url.pathname.startsWith("/api/") && request.method === "GET",
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
  resolve: {
    // "@/..." alias'i tsconfig'de de var ama onu SADECE TypeScript okur;
    // Vite'in kendi cozumleyicisi icin burada da tanimli olmali.
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  build: {
    manifest: true,
    chunkSizeWarningLimit: 500,
  },
  server: {
    // Compose icinde API_TARGET=http://api:8787 gelir; disarida npm run dev
    // ile calistirinca 127.0.0.1'e duser.
    proxy: { "/api": process.env.API_TARGET ?? "http://127.0.0.1:8787" },
    // Container icinde inotify calismiyor (Podman/Docker VM + bind mount):
    // dosyayi degistiriyorsun, HMR hic tetiklenmiyor. compose WATCH_POLLING=1
    // gonderir. Native Linux'ta 0 yaparak CPU'yu geri alabilirsin.
    watch: process.env.WATCH_POLLING === "1" ? { usePolling: true, interval: 400 } : undefined,
  },
});
