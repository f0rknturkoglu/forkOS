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
        // Precache tavani 4 MiB: Workbox varsayilani (2 MiB) buyuk yerel
        // parcalari sessizce disarida birakir ve offline kabuk eksik acilir.
        maximumFileSizeToCacheInBytes: 4 * 1024 * 1024,
        cleanupOutdatedCaches: true,
        importScripts: ["/sw-cleanup.js"],
        runtimeCaching: [
          {
            // OFFLINE = SADECE OKUMA.
            //
            // Beyaz liste YANIT SOZLESMESI uzerinden kurulur: ayni origin,
            // GET, `application/json` ve bilinen boyutu 256 KB'in altinda.
            // Bu uc kosul birlikte binary ve buyuk yanitlari (ekler, belge
            // dosyalari, medya gorselleri, disa aktarmalar) kendiliginden
            // disarida birakir; listenin bakimi gerekmez.
            //
            // Boyut tavani olmadan `maxEntries` yanilticidir: Workbox girdi
            // SAYISINI sinirlar, bayt miktarini degil.
            urlPattern: ({ url, request }) =>
              url.origin === self.location.origin && url.pathname.startsWith("/api/") && request.method === "GET",
            // AG ONCE (NetworkFirst), onbellek YEDEK.
            //
            // Neden StaleWhileRevalidate DEGIL: o strateji istegi ANINDA
            // onbellekten yanitlar ve agi arka planda tazeler. Mutasyondan
            // sonra `invalidateAfter(...)` ile yapilan tazeleme bu yuzden ESKI
            // yaniti aliyordu; ekran ancak 30 sn'lik yoklamadan (ya da tam
            // sayfa yenilemeden) sonra dogru hale geliyordu ("Odak seansi
            // bitirdim ama gosterge hala calisiyor").
            //
            // NetworkFirst sunucu ayaktayken HER ZAMAN taze veri verir.
            // Sunucu kapaliysa (offline = sadece okuma) baglanti reddi aninda
            // olur ve onbellekten okunur; `networkTimeoutSeconds` yalnizca ag
            // asili kaldiginda devreye girer, sinirsiz bekleme olmaz.
            handler: "NetworkFirst",
            options: {
              cacheName: "lifeos-api-v2",
              // Yerel sunucu icin cok kisa: cevrimdisi okuma en fazla bu kadar
              // bekler, sonra onbellege duser.
              networkTimeoutSeconds: 3,
              cacheableResponse: { statuses: [200] },
              // `options` semasinda `cacheWillUpdate` diye bir kisayol YOK
              // (workbox-build onu reddeder); desteklenen yol `plugins`.
              plugins: [
                {
                  // DIKKAT: bu fonksiyon uretilen service worker'a METIN
                  // olarak gomulur; disaridaki degiskenleri goremez. Esikler
                  // bu yuzden satir ici verilir.
                  cacheWillUpdate: async ({ response }) => {
                    const maxBytes = 256 * 1024;
                    // Kucuk JSON olsa bile cache'e girmemesi gereken uclar:
                    // disa aktarma ve yedek yanitlari buyuk/tek kullanimlik,
                    // digerleri binary dosya.
                    const excluded = [
                      /^\/api\/goals\/studio\//, // run state and approval revisions must never be served stale
                      /^\/api\/export\//,
                      /^\/api\/backup\//,
                      /^\/api\/documents\/[^/]+\/file$/,
                      /^\/api\/media\/assets\//,
                    ];
                    const contentType = response.headers.get("content-type") ?? "";
                    if (!contentType.includes("application/json")) return null;
                    const { pathname } = new URL(response.url);
                    if (excluded.some((pattern) => pattern.test(pathname))) return null;
                    // Boyut GOVDEDEN olculur. `Content-Length` gzip'li
                    // yanitlarda hic gelmez ve "yok"u 0 saymak tavani
                    // islevsiz birakir (nginx gzip'i buyuk JSON'u 400
                    // bayta indirir; baslik okunamayinca 400 KB'lik yanit
                    // sinirdan gecerdi).
                    const { size } = await response.clone().blob();
                    return size > maxBytes ? null : response;
                  },
                },
              ],
              expiration: {
                maxEntries: 120,
                maxAgeSeconds: 60 * 60 * 24 * 7,
                // Kota hatasinda tum cache'i bosalt: 256 KB tavani ve 120
                // girdi sinirina ragmen beklenmedik bir buyume olursa
                // browser'in keyfi tahliyesine birakma.
                purgeOnQuotaError: true,
              },
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
    // Ana uygulama hala scripts/check-bundle.mjs ile 500 KB sinirinda.
    // Bu esik yalniz Vite'in kendi uyari gurultusunu keser; giris chunk'i
    // sinirini check-bundle.mjs zorlar.
    chunkSizeWarningLimit: 2_500,
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
