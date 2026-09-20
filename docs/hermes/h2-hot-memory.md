# forkOS × Hermes — H2: Sıcak Küratörlü Hafıza (Hot Curated Memory)

> **Tek cümle:** H2, Hermes'e oturumlar arasında **hemen erişilebilir kalması
> gereken küçük, kullanıcı onaylı, kalıcı bağlamı** verir.

H2 ikinci bir bilgi tabanı DEĞİLDİR. Konuşma arşivi değildir. Otomatik
profil çıkarma değildir. RAG, embedding ya da yerel model içermez.

---

## 1. Üç bağlam katmanı

```text
forkOS               → "Şu an ne oluyor?"        (canlı operasyonel durum)
f0rknbrain Vault     → "Ne biliyoruz / ne karar verdik / ne araştırdık?"
90 Agent Hot Memory  → "Hangi küçük kalıcı gerçekler, hedefler, tercihler ve
                        kısıtlar ajanın her seferinde tüm kasayı taramadan
                        yanında taşıması gerekenler?"
```

Bu üç katman ayrı kalır. Sıcak hafıza, kasayı taramaya alternatif değil;
**tarama ihtiyacını azaltan küçük bir ön yüktür**.

---

## 2. Sahiplik

```text
Operasyonel durum        → forkOS PostgreSQL
Uzun biçimli insan bilgisi → normal f0rknbrain Vault
Sıcak küratörlü bağlam   → f0rknbrain / 90 Agent/Memory/
Konuşma                  → KALICI DEPO DEĞİLDİR
```

Yok olanlar: PostgreSQL ajan-hafıza tablosu, SQLite hafıza DB'si, JSON yan
dosyası, Redis, vektör DB, ayna kopya.

**Hermes'in kendi kalıcı hafızası kanonik sahip DEĞİLDİR.** Amaç harness
bağımsızlığıdır: yarın başka bir ajan ya da yerel model gelse bile hafıza
`Markdown + Obsidian + Git + kullanıcıya ait` kalır. Kurulum: `h2-setup.md`.

---

## 3. Depolama düzeni

```text
90 Agent/
└── Memory/
    ├── <memory-id>.md
    ├── <memory-id>.md
    └── ...
```

**Öğe başına tek dosya** — tek büyük `Profile.md` YOKTUR. Kazanç:

```text
daha küçük çakışma yüzeyi
öğe başına revizyon
güvenli emeklilik
sınırlı güncelleme
okunabilir Git geçmişi
tüm profili yeniden yazma zorunluluğu yok
```

Kategoriler (profile / preference / goal / constraint / decision) kavramsal
kalır; fiziksel olarak öğe başına dosyaya dağılır.

---

## 4. Kimlik ve adlandırma

```text
memory_id  = UUID (sunucu üretir)
dosya adı  = <memory_id>.md
```

**Yol kimlik değildir.** Başlık yalnızca frontmatter'da yaşar; dosya adından
güvenlik açısından hassas bir yol türetilmez. Bu, slug/temizleme
karmaşıklığını ortadan kaldırır ve kullanıcı dosyayı taşısa bile kimliği korur.

---

## 5. Frontmatter şeması (sürüm 1)

```yaml
---
agent_memory_version: 1
memory_id: 550e8400-e29b-41d4-a716-446655440000
memory_kind: preference
title: Planning style
status: active
importance: 2
source_mode: explicit_user
created_at: 2026-09-20T17:30:00+00:00
updated_at: 2026-09-20T17:30:00+00:00
expires_at: null
related_forkos_ids: []
tags:
  - planning
---
User prefers project-level plans and manageable chunks rather than rigid hourly schedules.
```

Gövde, hafızanın kendisidir.

**Bilinmeyen anahtarlar korunur:** kullanıcı Obsidian'da kendi alanını
eklerse güncelleme onu SİLMEZ; yalnızca H2'nin sahip olduğu anahtarlar
yönetilir (§31).

---

## 6. Türler

| Tür | Ne için | Örnek |
|---|---|---|
| `profile` | Kalıcı, hassas olmayan, yardımı belirgin şekilde iyileştiren olgular | "Birincil geliştirme yığını .NET, TypeScript ve Python." |
| `preference` | Kalıcı çalışma/etkileşim tercihi | "Saatlik program yerine proje düzeyinde plan tercih eder." |
| `goal` | Oturumlar arası orta/uzun vadeli hedef | "Ana kariyer yönü uzaktan backend işi." |
| `constraint` | Gelecekteki yardımın uyması gereken kalıcı kısıt | "Aynı anda büyük öğrenme hatları planlamaktan kaçın." |
| `decision` | Dar bir projeye sığmayan kapsayıcı karar | "Operasyonel durum forkOS'ta, kalıcı bilgi Obsidian'da tutulur." |

---

## 7. Sıcak hafıza NE DEĞİLDİR

```text
Proje dokümantasyonu değildir   → 20 Projects/ (ör. "RepoLens pgvector kullanır")
Canlı durum değildir            → forkOS (ör. "Yarın H2'yi bitir", "14:00 toplantı")
Günlük not değildir             → geçici duygu/durum ("bugün kafam dolu")
Görev veritabanı değildir
Konuşma arşivi değildir
```

Bir bilgi birden çok oturumda ve FARKLI bağlamlarda işe yarıyorsa sıcak
hafızaya adaydır; yalnızca bir projede anlamlıysa değildir.

---

## 8. Revizyon modeli

```text
revision = sha256(dosya baytları)
```

Revizyon **türetilir**; dosyanın İÇİNE yazılmaz, okuma araçlarıyla döner.
Güncelleme ve emeklilik `expected_revision` İSTER; uyuşmazsa:

```text
HOT_MEMORY_STALE  →  hiçbir yazma yapılmaz
```

Neden mtime değil: hafıza dosyaları çok küçüktür, hash ucuzdur, gerçek içerik
değişimini yakalar ve dosya sistemi zaman damgası çözünürlüğü önemsizleşir.
Ayrı bir sürüm tablosu YOKTUR.

---

## 9. Durum modeli

```text
status            = active | retired          (dosyada yazılı)
effective_status  = active | expired | retired (okuma anında hesaplanır)
```

- **Zaman aşımı:** `expires_at` geçmişse okuma anında `expired` olur; dosya
  DEĞİŞTİRİLMEZ. Arka plan zaman aşımı işçisi yoktur.
- **Emeklilik:** `status=retired`; dosya Vault'ta ve Git geçmişinde kalır.
  Emeklilik **silme değildir** ve öyle anlatılmaz.
- **Çakışma:** aynı `memory_id` iki dosyada varsa aktif bağlam fail-closed
  davranır (`HOT_MEMORY_CONFLICT`); rastgele biri seçilmez.

---

## 10. Bağlam bütçesi

Sıcak hafıza ancak KÜÇÜK olduğu için işe yarar. `hot_memory_context` çıktısı
sabit bütçeye tabidir:

```text
en fazla 24 aktif öğe
en fazla ~6000 karakter hafıza metni
tür başına: profile 5 | preference 6 | goal 5 | constraint 6 | decision 6
```

Sıralama deterministiktir:

```text
importance ↓   →   updated_at ↓   →   memory_id ↑ (kararlı eşitlik bozucu)
```

Kategori sırası sabittir: `profile, preferences, goals, constraints, decisions`.

Bütçe dışı kalan aktif öğe varsa dürüstçe bildirilir:

```text
truncated = true
active_total / returned_total / omitted_total
```

---

## 11. Okuma yolları veritabanısızdır

`hot_memory_context` ve `hot_memory_list` PostgreSQL'e BAĞIMLI DEĞİLDİR.
Yalnızca `related_forkos_ids` doğrulaması yapan yazmalar oturum açar. Böylece
veritabanı geçici olarak kapalıyken bile hafıza katmanı okunabilir kalır.

---

## 12. Vault erişilemezse

Beş aracın tamamı açıkça hata verir:

```text
HOT_MEMORY_UNAVAILABLE
```

DB'ye düşen bir yedek YOKTUR; Hermes'in kendi hafızasına ya da legacy Notlar
arşivine düşen bir yol da yoktur.

---

## 13. Yerellik ve gizlilik sınırı

forkOS/f0rknbrain H2 için **hiçbir dış ağ çağrısı yapmaz**. Ancak MCP araç
sonuçlarını Hermes tüketir: **Hermes uzak bir model sağlayıcısı kullanıyorsa
sıcak hafıza bağlamı o sağlayıcıya model girdisi olarak gidebilir.**

Bu yüzden sıcak hafıza küçük, hassas olmayan ve amaçlı kalmalıdır. Politika:
`h2-memory-policy.md`.

Ajan çıktısı mutlak dosya yolu taşımaz; makbuzlar ve listeler yalnızca
Vault köküne GÖRELİ yol döner.

---

## 14. İlgili belgeler

- `h2-memory-policy.md` — ne hatırlanır, ne hatırlanmaz, aday akışı.
- `h2-tool-contract.md` — 5 aracın tam sözleşmesi.
- `h2-setup.md` — Hermes yapılandırması ve gizlilik sınırı.
- `h1-safe-actions.md` — onay modeli, tazelik, makbuz.
- `roadmap.md` — H-serisi.
