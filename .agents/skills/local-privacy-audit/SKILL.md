---
name: local-privacy-audit
description: Yeni paket veya ağ mantığı eklerken uygulanır. Dışarıya veri sızıntısını (harici CDN, telemetri, bulut API'leri) statik kontrollerle engeller; 127.0.0.1 bind ve offline dayanıklılığını denetler.
globs: ["backend/**", "frontend/**", "extension/**"]
---

# local-privacy-audit — forkOS yerel-gizlilik denetimi

## Değişmez ilkeler (AGENTS.md "Yapma" + plan dokümanı)

forkOS **tek kullanıcılı, local-only** kişisel OS'tur. Dışarıya veri GİTMEZ.

1. **Harici API'ye veri gönderme yasak** — LLM API'leri dahil (Ollama gibi yerel modeller dahil değildir ama yine de kullanıcı onayı ister). Tüm servisler `127.0.0.1`'e bind.
2. **Yeni bağımlılık eklerken** (pyproject/package.json):
   - Telemetri/analiz SDK'ları, harici CDN script'i, font/piksel izleyici YOK. Frontend fontları `@fontsource` paketinden (yerel) gelir — Google Fonts CDN'ine `<link>` EKLEME.
   - Paket çözümleme: bu paket ağa veri yazar mı (docs/known telemetry)? Şüphede kalırsan ekleme.
3. **Ağ çağrılarının yönü:** backend'den dışa giden tek izin = kaynak çekme (scraper/RSS/github API/medya meta) — GİDEN veri değil, GELEN içerik. Kullanıcı verisi (notlar, todo, finans) hiçbir dış uca gidemez. `OAuthToken` (github/google) yedek DIŞIDIR (backup.py hariç tutar).
4. **Offline dayanıklılık:** yazma offline'da kapalı (`OfflineWriteError`, api.ts guard); extension kendi outbox'ına yazar (chrome.storage) ve geri gelince boşaltır. Yeni özellik bu sözleşmeyi bozamaz: mutation'lar ortak API katmanından geçer, `navigator.onLine` yok sayılmaz.

## Statik denetim (yeni ağ mantığı ekledikten sonra)

- Backend: `grep -rn "httpx\\|aiohttp\\|urllib\\|requests"` yeni kodda — her dış çağrının hedefini doğrula (kaynak URL'leri parametre; kullanıcı verisi taşımıyor).
- Frontend: `fetch(`, `axios`, `new WebSocket`, `<script src=http`, `@import url(` taraması — BASE `@/core/api` üzerinden gitmeyen çağrı kırmızı bayrak.
- Harici kaynak: `grep -rn "https://"` yeni frontend kodunda — yalnızca kaynak içerik URL'leri (rss item linkleri, media cover URL'leri) ve kullanıcının verdiği ayar linkleri.
- 127.0.0.1 bind: uvicorn/config `host` değeri loopback; CORS yalnızca `chrome-extension://` + kendi origin'i.

## Extension

- MV3: outbox idempotent (`client_uuid`); popup/background yerel backend'e (127.0.0.1) konuşur; başka ağ erişimi yok. Manifest izinleri en azda tutulur.

## Doğrulama

- Yeni kod için yukarıdaki taramaları koş; `git diff` ile eklenen `http`/`fetch` satırlarını tek tek gözden geçir.
- Şüpheli harici çağrıyı testte mock'la (gerçek ağa çıkma); kural ihlali görürsen kodu düzelt, sessizce geçme.
