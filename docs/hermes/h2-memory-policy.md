# forkOS × Hermes — H2 Hafıza Politikası

Bu belge **neyin sıcak hafızaya girdiğini** ve **nasıl girdiğini** tanımlar.
Mekanizma `hot_memory_store`'dur; buradaki kurallar o mekanizmanın ne zaman
kullanılacağını söyler.

> Sıcak hafıza, kullanıcının onayladığı küçük bir kalıcı bağlam katmanıdır.
> "Kullanıcı ne derse kaydet" değildir.

---

## 1. Uygunluk testi

Bir bilgi sıcak hafızaya aday olabilmesi için İLGİLİ tüm koşulları sağlamalıdır:

```text
1. Gelecekteki oturumlarda işe yarıyor mu?
2. Bugünün görevinin/olayının ötesinde kalıcı mı?
3. Canlı forkOS durumu olarak daha iyi temsil edilmiyor mu?
4. Yalnızca projeye özgü uzun biçimli bilgi değil mi?
5. Tek bir atomik hafıza olarak ifade edilecek kadar küçük mü?
6. Açık kullanıcı bilgisine mi dayanıyor (ya da kullanıcı görebileceği bir çıkarıma mı)?
7. Otomatik enjekte edilmemesi gereken hassas veri DEĞİL mi?
8. Kolayca yeniden bulunabilecek kamuya açık bir bilgi değil mi?
```

Sağlamıyorsa **aday önerilmez**.

---

## 2. Ne UYGUNDUR

```text
"Bundan sonra saatlik program istemiyorum."
→ preference: "Proje düzeyinde plan ve yönetilebilir parçalar tercih eder."

"Ana kariyer hedefim remote backend işi."
→ goal: "Ana kariyer yönü uzaktan backend işi."

"Aynı anda üç öğrenme hattı yürütmek bana iyi gelmiyor."
→ constraint: "Aynı anda büyük öğrenme hatlarını planlamaktan kaçın."

"Operasyonel durum forkOS'ta, bilgi Obsidian'da dursun."
→ decision: "Kişisel sistem mimarisi: operasyonel durum forkOS, kalıcı bilgi Obsidian."

"Genelde systems tarafında Rust tercih ediyorum."
→ preference: "Sistem odaklı kişisel araçlarda Rust tercih eder."
```

---

## 3. Ne UYGUN DEĞİLDİR

| Girdi | Doğru yer | Neden |
|---|---|---|
| "Yarın 14:00'te ALES çalışacağım." | `forkos_todo_create` / `forkos_todo_plan` | canlı durum |
| "RepoLens'te pgvector seçtik çünkü..." | proje bilgi notu (`brain_save_to_entity`) | projeye özgü |
| "Bugün kafam çok dolu." | normal yanıt; kalıcı değil | geçici durum |
| "RepoLens'in next_action'ı dogfood." | forkOS | operasyonel alan |
| "Türkiye'nin başkenti Ankara." | gerek yok | kolayca yeniden bulunur |
| "Geçen hafta şu hatayı çözdük." | Vault bilgisi / olay geçmişi | dar bağlam |

Bir proje kararı, **yalnızca** ilgisiz gelecek konuşmalarda da işe yarayacak
kadar kapsayıcıysa sıcak hafızaya girer.

---

## 4. Hassas veri dışlaması

Sıcak hafıza gelecekteki akıl yürütmeye enjekte edilir ve Hermes'in
kullandığı modele gidebilir. Bu yüzden muhafazakârdır.

**Proaktif olarak sıcak hafızaya YAZILMAZ:**

```text
parolalar, API anahtarları, token'lar, kurtarma kodları, özel anahtarlar
finansal hesap kimlikleri

tıbbi tanı ya da sağlık kayıtları
cinsel yaşam bilgisi
din, ırk/etnik köken, siyasi görüş ya da oy tercihi
adli sicil bilgisi

tam ev adresi, devlet kimlik numaraları, diğer yüksek riskli sırlar
```

Bu kategoriler sessizce ÇIKARILMAZ. Kullanıcı bunları normal Vault notu
olarak tutabilir; H2 tüm kasayı profile bağlama çevirmez.

**Apaçık sır koruması:** arka uç, deterministik olarak tanınabilen kimlik
bilgisi biçimlerini reddeder (`-----BEGIN ... PRIVATE KEY-----`, `Bearer <token>`,
`password=`/`api_key=`/`secret_key=` atamaları, `sk-…`, `ghp_…`). Yanıt:

```text
HOT_MEMORY_POLICY_REJECTED
```

Bu bir sınıflandırıcı DEĞİLDİR ve öyle sunulmaz. Asıl savunma şudur: küçük
şema + açık onay + net politika + otomatik yazma yasağı.

### 4.1 Yazma anı tek başına yetmez

Sıcak hafıza dosyaları Obsidian'da **elle düzenlenebilir**; bu bir özelliktir.
Bu yüzden araç üzerinden gelen içerik ile elle düzenlenmiş içerik AYNI
yüksek güvenli denetimden geçer:

```text
araç yazması      → HOT_MEMORY_POLICY_REJECTED (yazma reddedilir, dosya yok)
elle düzenleme    → dosya yüklenmez, DEĞİŞTİRİLMEZ, raporlanır
```

Elle düzenlenmiş politikaya takılan dosya:

```text
hot_memory_context ve hot_memory_list içinde GÖRÜNMEZ
brain_search(scope="agent") ve brain_read ile DE okunamaz
silinmez, yeniden yazılmaz, mtime'ı değişmez
yalnızca "politika nedeniyle dışlandı" sayacı/uyarısı ve göreli yol raporlanır
```

Sır, gövde ya da frontmatter hiçbir hata/warning/tanılama alanında
GÖRÜNMEZ. Bu kapsam **yalnızca `90 Agent/Memory`** içindir; normal Vault
bilgisi, günlük notlar ve kaynaklar bu politikaya tabi değildir.

> Denetim dar ve deterministiktir; "tüm hassas veri yakalanır" denmez.
> Kullanıcı hassas bilgisini normal Vault notu olarak tutmaya devam edebilir.

---

## 5. Aday akışı — konuşmada yaşar

Aday, onaylanana kadar **yalnızca Hermes'in mevcut konuşmasında** vardır.
Kalıcı bir aday deposu YOKTUR:

```text
memory_candidate tablosu    pending_memory tablosu
aday JSON dosyası           onay kuyruğu
aday işçisi
```

### 5.1 Açık "hatırla" isteği

```text
Kullanıcı: "Bunu hatırla: saatlik plan istemiyorum."
```

Hermes ek bir onay sorusu sormak zorunda değildir; yazma aracını doğrudan
çağırabilir. Onay kapısı zaten MCP istemcisindedir (`trust: untrusted`).

### 5.2 Çıkarımsal aday

Hermes kendiliğinden "bu hatırlanmaya değer" diye düşünürse:

```text
1. ÖNERİLEN hafızayı tam metniyle göster
2. Türünü söyle
3. Neden işe yarayabileceğini kısaca açıkla
4. Kullanıcıdan OLUMLU niyet al
5. Ancak ondan sonra hot_memory_store çağır
```

Sessiz profil çıkarma YASAKTIR.

---

## 6. Düzeltme akışı

Kullanıcı kalıcı bir olguyu düzeltirse, çelişen ikinci bir hafıza YARATILMAZ:

```text
1. hot_memory_list (ilgili terimle)
2. muhtemel mevcut öğeyi belirle
3. niyetlenen düzeltmeyi açıkla
4. hot_memory_update(expected_revision=...)
```

Birden çok aday eşleşiyorsa tahmin edilmez; hangi hafızanın değişeceği
konuşmada sorulur.

---

## 7. Emeklilik akışı

```text
Kullanıcı: "Bu hedef artık geçerli değil."
→ hot_memory_list → hedefi çöz → hot_memory_retire
```

Emeklilik **"bu hafızayı kullanmayı bırak"** demektir:

```text
dosya Vault'ta kalır
Git geçmişinde kalır
listelemeyle görünür
aktif bağlamdan ÇIKAR
```

"Her tarihsel kopyayı güvenle yok et" DEĞİLDİR ve öyle anlatılmaz. Fiziksel
silme H2'nin yüzeyinde yoktur; kullanıcının kendi kararıdır.

### 7.1 Sonradan yeniden hatırlama

```text
emekli   = bilinçli olarak artık aktif değil
expired  = zamanı dolduğu için artık aktif değil
```

Kullanıcı AYNI olguyu sonradan yeniden hatırlatırsa:

```text
eski kayıt canlandırılmaz (historiği yeniden yazmak olurdu)
aynı metin YENİ bir aktif kayıt olarak eklenir → yeni memory_id
eski kayıt yerinde ve emekli/süresi geçmiş hâlde kalır
```

```text
eski dönem : retired / expired kayıt (dosya yerinde)
yeni dönem : yeni aktif kayıt (yeni kimlik)
```

Aktif bir kaydın kesin tekrarı ise hâlâ `noop`'tur: gereksiz ikinci dosya
açılmaz. Bu kural **yalnızca kesin** (aynı tür + aynı normalize edilmiş metin)
eşleşmedir; bulanık/semantik benzerlik aranmaz.

---

## 8. Öncelik sırası

Hafıza bağlamdır, otorite değildir:

```text
1. Güncel açık kullanıcı talimatı
2. Güncel canlı forkOS durumu
3. Aktif sıcak hafıza
4. Genel Vault bilgisi / geçmiş
```

Örnek: hafıza "kısa cevap tercih eder" diyor, kullanıcı "bunu kapsamlı anlat"
dedi → **güncel talimat kazanır**.

---

## 9. Ne zaman sıcak hafıza OKUNUR

```text
Kişisel planlama / karar desteği  → hot_memory_context + ilgili H0 araçları
Genel kodlama/olgusal soru        → sıcak hafızayı ÇEKME (veri minimizasyonu)
Daha derin tarihsel bağlam gerek  → brain_search / brain_read
```

Örnek — "Napıyoruz?":

```text
hot_memory_context  +  forkos_briefing
```

Böylece hem "uzun vadede ne önemli" hem "bugün gerçekte ne oluyor" bilinir;
tüm kasayı dökmeye gerek kalmaz.

---

## 10. Hafıza değiştirmez: bilgi yazmak

| Araç | Anlamı |
|---|---|
| `brain_capture` | "Bu bilgiyi kasaya kaydet." |
| `brain_save_to_entity` | "Bunu proje/konu bilgi notuna ekle." |
| `hot_memory_store` | "Bu küçük gerçeği/tercihi/hedefi **tekrar eden ajan bağlamı** olarak tut." |

```text
"Şu makale notunu kaydet."        → brain_capture (sıcak hafıza DEĞİL)
"Saatlik plan istemediğimi hatırla." → hot_memory_store
```

---

## 11. Örnek diyaloglar

**A — Açık tercih**

```text
Kullanıcı: "Bundan sonra bana saat saat program çıkarma, bunu hatırla."
→ hot_memory_store(kind=preference, source_mode=explicit_user)
```

**B — Kalıcı hedef**

```text
Kullanıcı: "Ana kariyer hedefim remote backend işi, bunu aklında tut."
→ hot_memory_store(kind=goal)
Otomatik görev OLUŞTURULMAZ.
```

**C — Çıkarımsal aday**

```text
Hermes: "Bu kalıcı bir tercih gibi görünüyor: '…' Kaydedeyim mi?"
Kullanıcı onaylamazsa → YAZMA YOK.
```

**D — Geçici görev**

```text
"Yarın ALES çalış." → forkos_todo_create (sıcak hafıza DEĞİL)
```

**E — Proje kararı**

```text
"RepoLens'te pgvector seçtik çünkü…" → proje bilgi notu
```

**F — Düzeltme**

```text
"Artık systems projelerinde Rust kullanmak istiyorum."
→ list → eski tercih varsa update (çelişen ikili bırakma)
```

**G — Emeklilik**

```text
"Bu hedef artık geçerli değil." → retire (aktif bağlamdan çıkar, dosya kalır)
```

**H — İç gözlem**

```text
"Benimle ilgili neleri hatırlıyorsun?" → hot_memory_context
Eski/pasif kayıtlar istenirse → hot_memory_list(effective_status="all")
Konuşma geçmişinden YENİDEN KURMA yapılmaz.
```

**I — Kişiselleştirilmiş planlama**

```text
"Napıyoruz?" → hot_memory_context + forkos_briefing
```

---

## 12. Hermes davranış talimatı (kopyalanabilir)

```text
Use forkOS Hot Memory as the canonical persistent agent profile.
Do not silently create memories.
For personal planning/decision support, read hot_memory_context when
durable user context is relevant.
Do not fetch it for unrelated generic queries.
When the user explicitly asks to remember something, use hot_memory_store.
When you infer a candidate yourself, show the proposed memory and obtain
affirmative intent before storing it.
Prefer updating an existing matching memory over creating contradictions.
Retirement means "stop using", not deletion.
```

Bu talimat otomatik kurulmaz; kullanıcı kendi yapılandırmasına ekler.
