/*
 * Uretilen service worker'a `importScripts("/sw-cleanup.js")` ile girer
 * (bkz. vite.config.ts -> workbox.importScripts).
 *
 * Neden gerekli: API runtime cache'i `lifeos-api` -> `lifeos-api-v2` diye
 * yeniden adlandirildi. Expirasyon eklentisi yalnizca kendi cache'ini
 * yonetebildigi icin eski cache artik hicbir sey tarafindan budanmazdi;
 * binary ve buyuk yanitlarla dolu halde diskte kalirdi. Burada bir kez
 * siliniyor.
 *
 * Liste kasitli olarak sabittir ve BU dosya guncel cache adlarini ICERMEZ;
 * icerseydi her surum yukseltmesinde yeni cache de silinirdi.
 */
const LEGACY_API_CACHES = ["lifeos-api"];

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => LEGACY_API_CACHES.includes(key))
            .map((key) => caches.delete(key)),
        ),
      ),
  );
});
