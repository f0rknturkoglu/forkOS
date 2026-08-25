# Faz 0 — Kararlar (K1–K5)

**Tarih:** 25 Ağustos 2026
Her karar: **öneri** + tek cümle gerekçe. Kod davranışı değişmedi; yön kararları.

---

## K1 — `habit` modülü: kaldır mı, ekrana getir mi?

**Öneri: Kaldır.**

- `backend/app/modules/habit/` tam (models/router/schemas/service), API uçları
  çalışıyor, ama frontend'de **sıfır çağrı** (yalnızca üretilmiş api-schema).
  `/habits` rotası `TodoPage`'i `routineOnly` filtresiyle açıyor — habit ekranı yok.
- İşlevi `todo.recur` devralmış (`TodoComposer`/`TodoRow` recur seçiyor ve gösteriyor).
- **Veri durumu:** `habit` = 1 kayıt, `habit_log` = 1 kayıt (kişisel DB).
  Migration'da bu veriyi `todo` + `recur` olarak taşıyan adım yazılacak
  (Faz 1, madde 9).
- `review` servisi `Event.verb == "habit.checked"` geçmişini okuyor — `event`
  append-only olduğu için tarihsel veri modül kalktıktan sonra da okunabilir kalır.
- `habits` haritası `review`'da boş döner; sorun değil (eski kayıt yoksa).

**Gerekçe:** Ekranı olmayan, işlevi başka yere taşınmış bir modülü ve tablolarını
taşımak, ölü yüzeyi büyütmekten ucuz.

## K2 — Medya IA'sı: 7 rota kurulacak mı?

**Öneri: Evet, Faz 4'te kur.**

- `MediaFrontend.test.tsx` (352 satır, tamamı `describe.skip`) 7 rota bekliyor:
  `/media`, `/media/library`, `/media/collections`, `/media/upcoming`,
  `/media/stats`, `/media/trash`, `/media/:id`; `modules/media/index.ts` sadece
  2'sini kaydediyor.
- Backend uçları **hazır ve çağrılmıyor**: `collections` CRUD, `upcoming`,
  `dashboard`, `restore`, `permanent`.

**Gerekçe:** Backend tamamen yazılı; eksik olan sadece rota kaydı — test zaten
sözleşmeyi tutuyor.

## K3 — `saved_view`: kullanılacak mı, kaldırılacak mı?

**Öneri: Faz 4'te kullan — bookmark + fırsat + medya listelerine "görünümü kaydet".**

- `saved_view` tablosu (`core/models.py`) + `GET/POST /api/views`,
  `DELETE /api/views/{id}` uçları var; frontend'de **sıfır çağrı**.
- `today.widget_order`/`today.columns` ayarlarıyla aynı kategoride: DB'de duran
  ama ekranda olmayan özellik.

**Gerekçe:** Tablo + API + migration hazır; silmek değil, tek çubukla ekrana
bağlamak daha az iş.

## K4 — Kaynak sağlığı tek yer: hangisi?

**Öneri: `/health` tek yetkili sayfa.**

- Şu an üç yerde: `/sources` (opportunity modülü), `/health` (health modülü),
  `SettingsPage` (SettingsSourceHealth) — üçü farklı görünüyor (plan B8).
- `/sources` rotası `/health`'e yönlendirecek (Faz 6); Settings'te tek satırlık
  özet + link kalacak.
- Ayrıca `health` modülü şu an `opportunity/labels`'tan `sourceLabel` import
  ediyor (modüller arası import, plan B8) — Faz 2'de `core/labels.ts`'e taşınacak.

**Gerekçe:** Aynı bilginin üç farklı görünümü bakım maliyetini üçler; tek sayfa +
özet en az sürprizli düzen.

## K5 — Kullanılmayan uçlar: UI'ya çıkacak mı, silinecek mi?

**Öneri: Hepsi UI'ya çıkacak (Faz 4'te bağlanacak); Faz 1'de silinmeyecek.**

| Uç | Durum | Faz 4 aksiyonu |
|---|---|---|
| `POST /api/pomodoro/{id}/pause` · `/resume` | Migration `0022_pomodoro_pause` boşa gitmiş | PomodoroWidget + PomodoroPage düğmeleri |
| `POST /api/recurring-payments/{id}/pay` | `recurring.paid` verb'ü üretilemiyor | RecurringWidget "ödendi" düğmesi |
| `DELETE /api/study/areas/{id}` | Alan silinemiyor | StudyPage satır menüsü |
| `POST /api/notifications/dismiss-all` | Panelde "tümünü kapat" yok | NotificationPanel |
| `GET /api/documents/{id}/open` | Belge açma bağlı değil | DocumentsPage |

**Gerekçe:** Beşi de tek düğmelik/tek satırlık iş; silmek, yarım kalmış ürünü
geri almak yerine bitirmek daha ucuz.

---

## Ek karar — K1 dışında düzeltilen test altyapısı

Faz 0 baseline'ı sırasında iki pre-existing test hatası düzeltildi
(ayrıntı `docs/faz0-baseline.md`):
1. `test_media_domain_migration.py` — DB'yi 0026'da bırakıp sonraki tüm DB
   testlerini kırıyordu; artık her test head'e dönüyor.
2. `test_migrations.py` istisna listesine `application_history` (append-only log)
   ve `interview` (1:N alt kayıt) eklendi — AGENTS.md kural 1'in "destek tablosu"
   kategorisiyle aynı gerekçe, `plan_slot` ile aynı sınıf.

---

## Faz 5 kararı — Bugün paneli sütun ayarı (today.columns)

**Karar: kaldırıldı.** `today.columns` ayarı ne backend DEFAULTS'unda ne de
frontend'de var (Faz 1'de `todayColumns()` ile birlikte okuma kalktı). Panel
sabit 3 sütun (`dashboard-grid`); widget'lar `slot` + zorunlu `order` ile
diziliyor. 375/768/1280/1600px'te taşma yok (output/playwright/).

## Faz 5 notu — agenda kind'ları

`AgendaKind` 8 üye: calendar, todo, rss, media, opportunity, interview,
payment, study. Yeni son-tarihli/olaylı modül agenda'ya `kind` ekleyerek
girer; kırıcı değişiklik yok. Test: `tests/test_today_kinds.py`.
