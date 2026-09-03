---
name: frontend-design
description: UI bileşeni, sayfa veya CSS geliştirirken uygulanır. Ham form elemanlarını ve sabit renkleri engeller; @/core/ui bileşenlerini, tasarım token'larını, tipografi ve dark-mode kontrastını garanti eder.
globs: ["frontend/src/**/*.{tsx,ts,css}"]
---

# frontend-design — forkOS tasarım sistemi

## Kurallar (AGENTS.md KURAL 15 + koruyan test `frontend/src/core/designSystem.test.ts`)

1. **Ham form elemanları yasak.** `<input>`, `<select>`, `<textarea>`, `<input type=checkbox>` doğrudan YAZILMAZ — `frontend/src/core/ui` içindeki sarmalayıcılar kullanılır:
   `Input`, `Select`, `Checkbox`, `Range`, `NumberInput`, `FileInput`, `Chip`, `Button`, `IconButton`, `RowList`, `Section`, `Empty`, `Kbd`.
   - Özel durum: `FileInput` ile dosya seçimi, `ConfirmDialog`/`dialog.tsx` API'leri.
2. **Renk, boyut ve yarıçap yalnızca token'dan.** Sabit hex (`#fff`, `bg-[#...]`), `bg-[rgb(...)]`, `text-[13px]`, `h-[18px]` gibi keyfi değerler yasak. Kullan:
   - Renk: `bg-canvas/surface/surface-sunken/surface-hover`, `text-primary/secondary/muted`, `border-subtle/strong`, `bg-accent/danger/warn/ok`, `--overlay-scrim` (modal arkası), marka renkleri `--feed-*`.
   - Koyu tema: aynı token'lar CSS değişkeninden döner — kontrast otomatik. Dark mode'da doğrulamak için `:root[data-theme=dark]` altında render testi (varsa) ya da tarayıcı kontrolü.
3. **Tipografi.** Sans: IBM Plex Sans (varsayılan); serif başlık/okuma: Newsreader (`font-serif`, `.article-content`, `.numeral` yalnızca SAAT/SAYAÇ/SKOR gibi büyük sayı gösterimleri için — küçük sans rozetin içine serif numeral KOYMA, `tabular-nums` kullan). Sınıflar: `text-heading/title/body/meta/micro`, `label-caps`.
4. **Bileşen kontratı.** Mutation'lar: `invalidateAfter("modul.write")` (KURAL 14, dosyaya dokunma). Tipler `@/core/types` veya modül içi; `@/core/ui`'ya yeni bileşen eklemeden önce modülde kopya var mı bak (FilterChip örneği core'a taşındı).
5. **Erişilebilirlik.** Buton/ikon `aria-label`/`title`; klavye kısayolları odak kaybında da çalışmalı (window listener + input guard — ReviewSession örneği).

## Doğrulama

- `cd frontend && npx vitest run src/core/designSystem.test.ts` (token taraması modules+core+app+lib)
- `npx tsc -b` — tipler temiz.
- Görsel değişiklik: tarayıcıda gerçek yüzeyi doğrula (sadece DOM testi yetmez).

## Kaçın

- `bg-canvas/60` gibi opacity'li token kombinasyonları yalnızca aynı token ailesiyle.
- Bileşen kopyası: ikinci bir görsel desen yerine mevcut token/bileşen.
