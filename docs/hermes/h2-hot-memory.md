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

> **Sıcak hafızanın kimliği `memory_id`'dir; `forkos_id` DEĞİLDİR.**
> `forkos_id` yönetilen *bilgi notlarının* (Faz 3/Obsidian köprüsü) alanıdır.
> Sıcak hafıza frontmatter'ına `forkos_id` YAZILMAZ. Operasyonel bir kayda
> bağlam kurulduğunda hedef kimlik `related_forkos_ids` içinde taşınır.

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

### 8.1 Yetkili karşılaştırma (dosya sistemi CAS)

Revizyon denetimi İKİ katmanlıdır ve ikincisi tek başına yetkilidir:

```text
tarama anındaki revizyon karşılaştırması  = kolaylık (hızlı hata yolu)
dosyanın ŞU ANKİ baytlarının hash'i       = YETKİ
```

Yazma sırası bu yüzden şudur:

```text
geçici dosyaya yaz + fsync
→ GÜNCEL baytları oku, sha256 hesapla, expected_revision ile karşılaştır
→ uyuşuyorsa  os.replace (atomik)
→ uyuşmuyorsa HOT_MEMORY_STALE, hiçbir şey yazılmaz
```

Pahalı iş doğrulamadan ÖNCE yapılır ki doğrulama ile `os.replace` arasındaki
pencere tek bir sistem çağrısına insin. Bu pencere tamamen sıfır DEĞİLDİR:
doğrulamadan sonraki mikrosaniyeler içinde Obsidian'da yapılan bir düzenleme
yakalanmaz. Tek kullanıcılı, yerel-öncelikli mimaride bu kabul edilir; kilit
alt sistemi (`.lock`, danışma kilidi, DB mutex) KURULMAZ — süreçler arası
durumu dosya sistemi CAS'i korur.

### 8.2 Bayat revizyon, "değişiklik yok"tan ÖNCE kazanır

`hot_memory_update` ve `hot_memory_retire` şu sırayı izler:

```text
çözümle → çakışma → kaydı bul → GÜNCEL revizyonu doğrula
        → sağlanan alanlar → politika → sonraki durum → noop kararı → yazma
```

Sonuç: istenen değerler mevcut duruma EŞİT olsa bile, çağıran bayat bir
`expected_revision` gönderdiyse `HOT_MEMORY_STALE` döner — sessiz bir `noop`
makbuzu DEĞİL. Zaten emekli bir kayıt için de aynıdır: yalnızca GÜNCEL
revizyon `noop` alabilir.

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

### 9.1 Yeniden hatırlama: yeni dönem, yeni kimlik

Kesin tekrar denetimi YALNIZCA `effective_status == active` kayıtlar için
uygulanır:

```text
aktif kayıt + aynı tür + aynı normalize edilmiş metin  → noop (yeni dosya yok)
emekli kayıt + aynı metin                              → YENİ AKTİF kayıt
süresi geçmiş kayıt + aynı metin                       → YENİ AKTİF kayıt
```

Eski kayıt **canlandırılmaz** ve **değiştirilmez**; yeni kayıt yeni bir
`memory_id` alır. Tarih dürüst kalır:

```text
eski dönem : retired / expired kayıt (dosya yerinde)
yeni dönem : yeni aktif kayıt (yeni kimlik)
```

Aksi davranış kullanıcıyı sessizce çıkmaza sokardı: "bunu hatırla" derdi ama
emekli kopya yüzünden hiçbir şey aktif olmazdı.

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

Okunabilirlik ÖNCEDEN doğrulanır: kök yapılandırılmış mı, var mı, dizin mi,
okunabilir mi. Okuma sırasında oluşan ham bir dosya sistemi istisnası da aynı
koda çevrilir; ajan yığın izi, mutlak yol ya da kullanıcı adı GÖRMEZ.

`90 Agent/Memory` **yoksa** bu bir hata değildir: boş hafızadır. Hiçbir okuma
yolu dizini oluşturmaz; dizin yalnızca onaylı bir yazmada doğar.

---

## 13. Depolama güvenceleri

### 13.1 Oluşturma üzerine yazmaz (birincil yolda atomik)

```text
tam içerik → geçici dosya (+fsync) → os.link(geçici, hedef) → geçici silinir
```

`os.link` hedef VARSA `FileExistsError` verir; yani "varsa üzerine yaz"
değildir. Hedef yalnızca içeriği TAM olan bir dosyaya işaret ettiği için kısmi
bir Markdown dosyası hiçbir an görünmez. Başarısız oluşturma ne yarım hedef ne
de artık geçici dosya bırakır.

Her iki yolda da politika denetimi yayından ÖNCE çalışır: sır taşıyan bir aday
ne hedef dosya ne dizin yaratır.

> Sert bağ desteklemeyen dosya sistemlerinde (bazı ağ/FUSE mount'ları) yayın
> `O_CREAT|O_EXCL` yoluna düşer: üzerine yazma yine engellenir, ancak **kısmi
> görünürlük garantisi o senaryoda geçersizdir**. İki yol aynı garantiyi
> VERMEZ ve öyle sunulmaz.

### 13.2 Güncelleme atomiktir

Aynı dizinde geçici dosya + `os.replace`. Kısmi YAML/Markdown hiçbir an
görünmez ve başarısız güncelleme geçici dosya bırakmaz.

### 13.3 Tanılama sayaçları gerçeği söyler

```text
invalid_count      = şema dışı + politika dışı dosyaların GERÇEK sayısı
invalid_paths      = yalnızca ilk MAX_INVALID_REPORTED göreli yol (20)
policy_rejected_count = yalnızca politika nedeniyle dışlananlar
```

Tanılamadaki yollar **redakte edilir**: sır benzeri dosya adı bileşenleri
`[redacted]` ile değiştirilir ve mutlak yol hiçbir koşulda döndürülmez. Aynı
kural çakışma hatalarında da geçerlidir. Bozuk ya da politika dışı dosyalar
okuma sırasında **düzeltilmez**.

50 bozuk dosya varsa `invalid_count` 50'dir; yol listesi 20'de kesilir. Sayaç
ile liste birbirinden bağımsızdır ki tanılama yalan söylemesin.

---

## 14. Yerellik ve gizlilik sınırı

forkOS/f0rknbrain H2 için **hiçbir dış ağ çağrısı yapmaz**. Ancak MCP araç
sonuçlarını Hermes tüketir: **Hermes uzak bir model sağlayıcısı kullanıyorsa
sıcak hafıza bağlamı o sağlayıcıya model girdisi olarak gidebilir.**

Bu yüzden sıcak hafıza küçük, hassas olmayan ve amaçlı kalmalıdır. Politika:
`h2-memory-policy.md`.

### 14.1 Politika OKUMA anında da uygulanır

Sıcak hafıza dosyaları Obsidian'da elle düzenlenebilir; yazma anındaki kontrol
tek başına yetmez. Denetim **TAM artifact** üzerindedir:

```text
politika girdisi = göreli yol + dosyanın HAM Markdown içeriği
```

Yalnızca başlık ve gövdeyi taramak; `tags`, `retired_reason`, bilinmeyen
frontmatter ve taşınmış dosya adı gibi kullanıcı denetimindeki diğer metinleri
kaçırırdı. Sıcak hafıza dosyaları küçüktür; tam tarama ucuzdur ve ayrışan alan
listeleri bakımı gerektirmez. Yazmada da AYNI kapı çalışır: render edilen aday
yayınlanmadan önce denetlenir, yani reddedilen metadata ne hedef dosya ne dizin
yaratır.

Eşleşen dosya:

```text
sıcak hafıza bağlamına YÜKLENMEZ  (hot_memory_context / hot_memory_list)
KULLANICININ DOSYASI DEĞİŞTİRİLMEZ (silinmez, yeniden yazılmaz, mtime'a dokunulmaz)
raporlanır: sayaç + "politika nedeniyle dışlandı" uyarısı
```

Aynı dosya H0 yüzeyinden de dışlanır (`brain_search(scope="agent")`,
`brain_read`): aksi hâlde H2'nin engellediği içerik başka bir araçla model
bağlamına girebilirdi. Bu kural **yalnızca `90 Agent/Memory`** ağacına
uygulanır; normal kasa bilgisi, günlük notlar ve kaynaklar etkilenmez.

Ajan çıktısı mutlak dosya yolu taşımaz; makbuzlar ve listeler yalnızca
Vault köküne GÖRELİ yol döner. Politika dışı bir dosya için bile sır, gövde ya
da frontmatter raporlanmaz — yalnızca göreli yol ve sayı.

> Denetim YÜKSEK GÜVENLİ ve DAR'dır: yalnızca apaçık kimlik bilgisi biçimlerini
> yakalar. "Tüm hassas veri bulunur" İDDİA EDİLMEZ; asıl savunma küçük şema,
> açık onay ve otomatik yazma yasağıdır.

---

## 15. İlgili belgeler

- `h2-memory-policy.md` — ne hatırlanır, ne hatırlanmaz, aday akışı.
- `h2-tool-contract.md` — 5 aracın tam sözleşmesi.
- `h2-setup.md` — Hermes yapılandırması ve gizlilik sınırı.
- `h1-safe-actions.md` — onay modeli, tazelik, makbuz.
- `roadmap.md` — H-serisi.
