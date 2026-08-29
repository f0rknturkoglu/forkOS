# Today Akışı ve Proje Günlüğü Uygulama Planı

> Bu plan, `docs/superpowers/specs/2026-08-29-today-project-journal-design.md` tasarım kararlarını uygular. Her görev önce başarısız test, sonra en küçük uygulama ve doğrulama sırasıyla tamamlanır.

## Faz 1 — Today sol panelini yoğunlaştır ve tamamlamayı görünür yap

**Dosyalar:**
- Değiştir: `frontend/src/modules/today/TodayAgendaWidget.test.tsx`
- Değiştir: `frontend/src/modules/today/TodayAgendaWidget.tsx`

1. Üçten fazla öneri ve tamamlanmış görev içeren fixture ekle.
2. Yalnızca iki önerinin göründüğünü, “Tamamlananlar”ın varsayılan kapalı olduğunu ve açılıp kapanabildiğini test et.
3. Açık todo satırında görünür “Tamamla” eylemi bulunduğunu ve doğru mutation’ı çağırdığını test et.
4. `TodayAgendaWidget` içinde önerileri `slice(0, 2)` ile sınırla.
5. Tamamlananlar bölümünü erişilebilir bir disclosure/accordion yap; `aria-expanded` ve kontrollü içerik kullan.
6. `interactive` satırlara tasarım sistemiyle uyumlu tamamla butonu ekle; context-only ve tamamlanmış satırlarda gösterme.
7. İlgili frontend testlerini çalıştır.

## Faz 2 — Today akışını varsayılan görünür ve kaynak bazında dayanıklı yap

**Dosyalar:**
- Değiştir: `frontend/src/core/todayWidgets.test.ts`
- Değiştir: `frontend/src/core/registry.ts`
- Değiştir: `frontend/src/modules/today/index.ts`
- Oluştur: `frontend/src/modules/today/widgets/FeedStreamWidget.test.tsx`
- Değiştir: `frontend/src/modules/today/widgets/FeedStreamWidget.tsx`

1. `today.feed-stream` widget’ının yeni/varsayılan düzende görünür olduğunu test et.
2. Eski varsayılan-hidden tercihinin kullanıcı Today düzenine henüz dokunmadıysa widget’ı gizlememesini; açıkça gizleyen kullanıcı tercihinin korunmasını test et.
3. Widget kaydını `defaultVisible: true` yap ve registry tercih okumasına geriye uyumlu geçiş ekle.
4. RSS, Hacker News veya GitHub’dan biri hata verirken diğer kaynakların görünmeye devam ettiğini test et.
5. Her başarısız kaynak için kompakt hata durumu ve yalnız o kaynağı yeniden deneyen buton ekle.
6. Widget ve registry testlerini çalıştır.

## Faz 3 — Proje günlük notu veri modelini ve API’sini kur

**Dosyalar:**
- Oluştur: `backend/tests/test_project_journal.py`
- Oluştur: `backend/alembic/versions/0029_project_journal.py`
- Değiştir: `backend/app/modules/note/models.py`
- Değiştir: `backend/app/modules/note/schemas.py`
- Değiştir: `backend/app/modules/note/service.py`
- Değiştir: `backend/app/modules/project/models.py`
- Değiştir: `backend/app/modules/project/schemas.py`
- Değiştir: `backend/app/modules/project/service.py`
- Değiştir: `backend/app/modules/project/router.py`

1. Proje oluşturup bugünün günlük notunu ekleyen, aynı günü güncelleyen, timeline olaylarıyla gün bazında döndüren, geleceği reddeden ve boş içerikle notu silen API testleri yaz.
2. `note` tablosuna opsiyonel `project_id` ve `journal_day` alanları ekle; `(project_id, journal_day)` benzersizliği ve alanların birlikte dolmasını sağlayan constraint oluştur.
3. Günlük not yaratırken mevcut entity helper’larını, `notes_about` linkini ve append-only event kaydını kullan.
4. `GET /projects/{id}/journal` ve `PUT /projects/{id}/journal/{day}` uçlarını ekle. Uygulama yerel tarihinden sonraki günleri 400 ile reddet.
5. Günlük yanıtını gün bazında, yeni tarihten eskiye; not ve immutable proje olaylarını birlikte döndürecek şekilde oluştur.
6. Eski `project.notes` alanını model, şema ve migration’dan kaldır; mevcut veri için taşıma yapma.
7. Backend testlerini ve migration testlerini çalıştır.

## Faz 4 — Proje Notlar ve Timeline arayüzlerini tek Günlükte birleştir

**Dosyalar:**
- Oluştur: `frontend/src/modules/projects/ProjectJournal.test.tsx`
- Oluştur: `frontend/src/modules/projects/ProjectJournal.tsx`
- Değiştir: `frontend/src/modules/projects/ProjectsPage.tsx`
- Değiştir: `frontend/src/modules/projects/types.ts`
- Sil: `frontend/src/modules/projects/ProjectTimeline.tsx`

1. Bugünün seçili gelmesini, geleceğin seçilememesini, gün notunun blur’da PUT ile kaydedilmesini ve boş notun silme semantiğiyle gönderilmesini test et.
2. Gün gruplarında not ile proje olaylarının aynı tarih altında birlikte görünmesini test et.
3. `ProjectJournal` bileşenini mevcut `Input`, `Textarea`, `Button`, `Chip` ve tasarım tokenlarıyla oluştur.
4. Mutation sonrası `invalidateAfter("note.write", "project.write", "link.write")` kullan; offline yazmayı kapat.
5. `ProjectsPage` içindeki ayrı `Notlar` ve `ProjectTimeline` bloklarını kaldırıp `ProjectJournal` ekle.
6. Kullanılmayan `ProjectTimeline` dosyasını ve `Project.notes` frontend tipini kaldır.
7. İlgili frontend testlerini çalıştır.

## Faz 5 — Entegrasyon, sözleşme ve son doğrulama

**Dosyalar:**
- Gerekirse değiştir: OpenAPI snapshot/üretilmiş istemci dosyaları
- Gerekirse değiştir: endpoint coverage allowlist/testleri

1. Backend tam test paketini çalıştır.
2. Frontend typecheck, unit test, endpoint coverage ve production build çalıştır.
3. Docker servislerinde migration’ı uygula; Today ve Projects akışlarını tarayıcı üzerinden smoke test et.
4. `git diff --check`, `git status` ve son diff incelemesi yap.
5. Değişiklikleri mantıksal commitlere ayır ve tamamlanan davranışlarla kalan riski raporla.
