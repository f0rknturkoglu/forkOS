# forkOS — Faz 13: "Bugüne al" ile görev ekleme

> **Ön koşul:** Faz 0–12 tamamlandı (`617d934` + kalıntı düzeltmeleri).
> Faz 9'da kurulan plan / son-tarih ayrımının doğal devamı.

## Sorun

Yeni bir görev eklendiğinde Bugün panelinin sol sütununa düşmüyor.

Sebep bir bug değil, `agenda()` filtresinin sonucu —
[backend/app/modules/today/service.py:237](backend/app/modules/today/service.py):

```python
relevant = or_(
    Todo.id.in_(planned_ids),                                        # bugüne planlanmış
    and_(Todo.status.in_(("open", "doing")),
         or_(Todo.due_at < end,                                      # son tarihi bugün/geçmiş
             and_(Todo.recur.is_not(None), Todo.due_at.is_(None)))), # ya da rutin
    and_(Todo.status == "done", ...),                                # bugün tamamlanmış
)
```

Yeni görevin `due_at` boş, `recur` boş, plan slotu yok → üçüne de uymuyor.
(SQL inceliği: `due_at` NULL iken `due_at < end` ifadesi `TRUE` değil `NULL`
döner, satır elenir.)

Görev yalnızca `suggestions.todos`'a düşüyor: widget'ın en altı, "planına
yazılmadı" notu, **en fazla 4 kayıt**, sıralama öncelik ↓ → son tarih ↑ →
**oluşturma tarihi ↑**. Yani aynı öncelikteki tarihsiz görevler arasında en yeni
olan en sonda; 4+ açık görev varsa yeni eklenen listeden düşüyor. "oto" ayarı
kapalıysa bölüm hiç render edilmiyor.

**Seçilen çözüm (a):** ekleme anında niyeti sor. `due_at` yazma — Faz 9'da
kurulan `plan_slot` kavramını kullan.

## Kapsam

**İçinde:** `TodoComposer` (Görevler sayfasındaki ekleme formu) ve onu besleyen
backend sözleşmesi.

**Dışında** (bilerek — agent bunlara dokunmasın):
- `todo.quick` command palette komutu
- `ProjectTodos` içindeki görev ekleme
- `agenda()` filtresinin kendisi ve öneri limiti

İkisi de aynı backend alanını sonradan bedavaya kullanabilir; bu fazda
kapsam genişletme.

---

## PROMPT — FAZ 13

```
forkOS deposunda (/Users/furkanturkoglu/Downloads/forkOS) çalışıyorsun.
AGENTS.md ve CLAUDE.md'yi oku — özellikle kural 3 (log_event), 13 (EntityTypeSpec),
14 (invalidateAfter), 15 (tasarım tokenları). docs/mimari.md'de plan/son-tarih
ayrımını gözden geçir.

GÖREV: Görev eklerken "bugüne al" seçeneği ekle. İşaretliyse görev bugüne
PLANLANSIN (plan_slot), son tarih VERİLMESİN.

SORUN (teşhis edilmiş, tekrar araştırma):
  backend/app/modules/today/service.py:237  agenda() `relevant` filtresi
  Bir görev "Yapılacaklar"a ancak şu üçünden biriyle giriyor:
    1. bugüne planlanmış (plan_slot)
    2. açık/devam eden VE (due_at bugün/geçmiş VEYA rutin)
    3. bugün tamamlanmış
  Yeni görev: due_at NULL, recur NULL, plan slotu yok → hiçbirine uymuyor.
  Yalnızca suggestions.todos'a düşüyor: en fazla 4 kayıt, sıralamada en yeni
  en sonda, "oto" kapalıysa hiç görünmüyor.

ÇÖZÜM YÖNÜ — DEĞİŞTİRME:
  due_at SET ETME. Faz 9'da plan ile son tarihi bilerek ayırdık:
  "bugün yapmayı planlıyorum" ≠ "bugün teslim". due_at yazarsan yarın o görev
  gecikmiş görünür, öncelik sıralaması ve deadline sağlayıcıları bozulur.
  agenda() filtresini de gevşetme — Bugün paneli açık görev çöplüğü olmamalı.
  Doğru çözüm: kullanıcı ekleme anında "bugüne al" derse plan_slot yaz.

1. BACKEND — TEK İSTEKTE ATOMİK YAZMA:
   TodoIn şemasına opsiyonel alan ekle:
     plan_day: date | None = None
   todo_service.create() bu alan doluysa aynı transaction içinde plan slotunu
   da yazsın.

   REPODA HAZIR DESEN VAR, onu izle — backend/app/modules/review/service.py:251
     todo = await todo_service.create(session, TodoIn(...), commit=False)
     await todo_service.schedule(session, PlanSlotIn(entity_id=todo.id, day=...),
                                 commit=False)
   Aynı biçimde tek commit'te bitir.

   NEDEN TEK İSTEK: frontend'den iki ayrı çağrı (POST /todos + POST /plan)
   yaparsan ikincisi başarısız olduğunda görev oluşmuş ama planlanmamış olur —
   kullanıcı yarı yazılmış bir durumla kalır. Tek endpoint bunu ortadan kaldırır.

   - schedule() zaten log_event("plan.scheduled") atıyor; ayrıca todo.created
     event'i de yazılıyor. İkisi de kalsın (kural 3), yeni verb uydurma.
   - schedule() aynı (entity_id, day) için mevcut slotu güncelliyor — idempotent,
     dokunma.
   - plan_day geçmiş bir gün olabilir mi? Kararını ver ve doğrulama ekle;
     en azından şemada tip güvenliği olsun.

2. FRONTEND — TodoComposer:
   frontend/src/modules/todo/TodoComposer.tsx (yalnız TodoPage kullanıyor)
   - Açılan detay alanına "bugüne al" onay kutusu ekle.
     core/ui.tsx:442'deki Checkbox primitive'ini kullan — ham <input> YASAK
     (kural 15, designSystem.test.ts koruyor).
   - İşaretliyse create mutation'ına plan_day gönder.
   - Etiket net olsun: "bugüne al" (plan) ile mevcut tarih alanı (son tarih)
     karışmasın. Gerekirse tarih alanının etiketini de netleştir
     ("son tarih" gibi) — kullanıcı ikisinin farkını formda görmeli.

   VARSAYILAN DEĞER — karar ver ve gerekçelendir:
     Öneri: varsayılan KAPALI, ama son seçim localStorage'da hatırlansın.
     ("Frontend'de localStorage dışında kalıcı depolama varsayma" kuralı
      localStorage'ı meşru kılıyor.) Her zaman bugüne alan kullanıcı bir kez
     işaretler, o tercih kalır; hiç istemeyen etkilenmez.
     Farklı bir karar verirsen kod yorumunda gerekçesini yaz.

3. "BUGÜN" HANGİ GÜN — DİKKAT, BURADA GERÇEK BİR TUZAK VAR:
   Repoda iki ayrı "bugün" yardımcısı var ve AYNI ŞEYİ YAPMIYORLAR:
     frontend/src/lib/date.ts::localDateKey()      → Europe/Istanbul'a göre
     TodayAgendaWidget.tsx:42::localDay()          → tarayıcının yerel saatine göre
   Makine Istanbul saatinde değilse ikisi farklı gün üretir.

   plan_day'i agenda'nın SORDUĞU günle aynı helper'dan üret, yoksa görev
   panelin göstermediği bir güne planlanır — yani düzeltmeye çalıştığımız
   hatanın aynısı geri gelir.

   Bu iki helper'ın ayrışmasını da çöz: tek bir kaynağa indir (öneri:
   lib/date.ts::localDateKey; backend zaten Europe/Istanbul'da hesaplıyor —
   app/config.py settings.timezone). localDay() kaldırılıyorsa kullandığı
   yerleri güncelle. lib/dateUsage.test.ts guardrail'ine yeni dosyaları ekle.

4. INVALIDATION (kural 14):
   Görev + plan tek istekte yazıldığı için mutation iki olayı da bildirmeli:
     invalidateAfter("todo.write", "plan.write")
   Ham invalidate( kullanma; invalidation.test.ts bunu zaten yasaklıyor.

5. TESTLER:
   backend:
     - plan_day dolu → todo oluşuyor VE aynı gün için plan_slot yazılıyor
     - plan_day dolu → todo.due_at NULL kalıyor (regresyon koruması, bu fazın özü)
     - plan_day boş → plan_slot YAZILMIYOR (mevcut davranış korunuyor)
     - plan_day ile oluşturulan görev GET /today/agenda?day=<o gün> çıktısında
       checklist içinde geliyor (suggestions'ta değil) — asıl kanıt bu
   frontend:
     - onay kutusu işaretliyken POST /todos gövdesinde plan_day var
     - işaretsizken plan_day YOK
     - son seçim hatırlanıyor (localStorage kararını uyguladıysan)

6. DOKÜMAN:
   docs/mimari.md'de plan/son-tarih bölümüne bu akışı ekle: görev ekleme anında
   plan verilebiliyor, due_at ayrı bir kavram olarak kalıyor.

DOĞRULAMA:
  cd backend && python scripts/export_openapi.py
  cd frontend && npm run api:generate && npm run api:check
  cd frontend && npx vitest run && npm run build && npm run format:check
  node scripts/check-endpoint-coverage.mjs && node scripts/check-dead-exports.mjs
  make test CO="docker compose"
  cd backend && ruff check app tests scripts

ELLE AKIŞ (asıl kabul kriteri):
  /todos'ta "bugüne al" işaretli bir görev ekle →
    - görev Bugün panelinin sol sütununda "Yapılacaklar" altında görünüyor
      (en alttaki "Öneriler" bölümünde DEĞİL)
    - /todos'ta Faz 9'da eklenen plan çipi ("bugün planlı") görünüyor
    - görevin son tarihi boş
  İşaretlemeden bir görev ekle → eski davranış, panelde Yapılacaklar'da yok.

ÇIKTI: eklenen alan, varsayılan değer kararı ve gerekçesi, iki "bugün"
helper'ının nasıl tekleştirildiği, testler, elle akış sonucu.
```

---

## Sonraki adım için not (bu fazın parçası değil)

`plan_day` alanı eklendikten sonra şunlar tek satırla aynı davranışı kazanabilir:

- `todo.quick` komutu (`modules/todo/index.ts`) — Bugün bağlamından çağrıldığında
- `ProjectTodos` — proje görevini doğrudan bugüne alma
- `OpportunityDetail` başvuru adımları

Hepsi aynı `POST /todos` ucunu kullanıyor. Ayrı faz olarak değerlendir.
