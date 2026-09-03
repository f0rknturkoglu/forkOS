---
name: resilient-scraping
description: İş ilanı veya RSS scraper'ı yazarken/düzeltirken uygulanır. SourceAdapter mimarisini, schema.org/JSON-LD önceliğini, bot/rate-limit dayanıklılığını ve "3 boş çalışma = bildirim" kuralını uygulatır.
globs: ["backend/app/sources/**", "backend/app/modules/rss/**", "backend/app/modules/opportunity/sync.py"]
---

# resilient-scraping — forkOS kaynak katmanı

## Kurallar (AGENTS.md KURAL 5, 6 + `backend/app/sources/base.py`)

1. **Her yeni scraper = `SourceAdapter`.** Worker'ın içine GÖMME; sözleşme `app/sources/base.py`'deki protokol. İleride VPS'e taşınabilmeli. Kayıt: `app/sources/.../scrapers/index.py` veya `_MODULES` benzeri tek kayıt noktası (pkgutil keşfi kullanılıyorsa dosya adı yeterli).
2. **Her koşu `source_run`'a yazar** (status ok/error/empty + items_found). Üst üste 3 `empty` → bildirim (sessiz ölüm kabul edilemez). Koruyan testler: kaynak test klasörlerindeki fixture tabanlı testler + `source_run` assertion'ları.
3. **Doğrulanamayan kaynağı sahte yazma.** Canlı test edemediğin scraper'ı "çalışıyor" diye bırakma: `blocked.py` içinde dürüst `status="blocked"` + açıklama (landingjobs/honeypot/offerzen/justjoinit örneği).
4. **Yapısal öncelik.** Sayfa içi yapılandırılmış veri: JSON-LD/schema.org önce; microdata/OpenGraph sonra; CSS seçici son çare. Tarih/konum normalizasyonu ortak helper'lardan (`country_code()`, `_normalize_*` — tekrar yazma).
5. **Bot dayanıklılığı.**
   - `Retry-After` başlığına saygı (429/503): bekleyip yeniden dene — `app/sources/scrapers/base.py` ortak yardımcıları kullan.
   - robots.txt engeli/site kuralları: saygı göster, sayfayı zorlama.
   - Timeout + `raise_for_status` + bağlam hatalarını yakala; yarım veriyi "başarı" sayma.
   - `CACHE_DIR`/asset yolları ORTAK sabitten (mutlak); scraper içinde sabit yol tanımlama.
6. **Feed tarayıcıları** (RSS): conditional GET (etag/last_modified), feed başına jitter'lı aralık, `error_count >= 5` → active=false + bildirim. Özellikler `source_run` ile ölçülür.

## İş ilanı (forkjob) ekstra

- `app/sources/forkjob_core/` altında modüler scraper dosyaları; `geo.py`/`models.py`/`normalize.py` ortaklarını kullan.
- Silinen/engellenen kaynakları `blocked.py`'ye taşı, dosyayı silme (keşif listesi bozulmasın).

## Doğrulama

- Kaynağın kendi fixture testi: `cd backend && <test DB URL> python -m pytest tests/sources/... -q` (gerçek ağa çıkma — fixture HTML kullan).
- Koşu sağlığı: `curl localhost:8787/api/sources/health` — her kaynak ok/error/empty görünür.

## Kaçın

- `time.sleep` döngüsü yerine backoff/Retry-After; gizli beklemeler.
- Siteye aynı anda N paralel istek; yalnızca tek makine local çalışma varsayımıyla bile nezaket sınırı koy.
