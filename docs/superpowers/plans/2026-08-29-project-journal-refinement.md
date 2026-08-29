# Project Journal Refinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Proje günlük notunu ve günün olaylarını tek yüzeyde birleştirip teknik `note.*` event adlarının kullanıcıya görünmesini engellemek.

**Architecture:** Backend proje günlüğü, not içeriğini `note` tablosundan döndürürken note yaşam döngüsü event'lerini yalnız global event akışında bırakır. Frontend seçili günü tek aktif çalışma kartı olarak render eder; geçmiş liste seçili günü dışarıda bırakır ve ham event verb'leri için güvenli insan dili fallback'i kullanır.

**Tech Stack:** FastAPI, SQLAlchemy async, React 18, TanStack Query, TypeScript, Vitest, Testing Library, Tailwind tasarım tokenları.

## Global Constraints

- `event` tablosu append-only kalır; hiçbir event update/delete edilmez.
- Entity ve Note yazma akışı değişmez; `create_entity`, `touch_entity`, `delete_entity`, `log_event` sözleşmeleri korunur.
- Yeni renk, radius, bağımlılık veya ham form kontrolü eklenmez.
- Görünür kullanıcı metninde ham `note.created` veya başka teknik verb gösterilmez.
- Offline yazma kapalı, okuma açık kalır.

---

### Task 1: Proje günlüğü event semantiğini düzelt

**Files:**
- Modify: `backend/tests/test_project_journal.py`
- Modify: `backend/app/modules/project/service.py`

**Interfaces:**
- Consumes: `journal(session, project_id, limit) -> list[dict]`, `/api/activity` append-only event cevabı.
- Produces: Journal gruplarında `note` içeriği korunur; `events` içinde `note.*` bulunmaz.

- [ ] **Step 1: Failing backend testini yaz**

`test_project_journal_upserts_one_entity_backed_note_per_day` içinde journal event doğrulamasını aşağıdaki sözleşmeye çevir:

```python
verbs = {event["verb"] for event in today["events"]}
assert "project.created" in verbs
assert not any(verb.startswith("note.") for verb in verbs)

activity = (await client.get("/api/activity", params={"limit": 100})).json()
note_events = [
    event for event in activity
    if event["entity_id"] == first_note["id"] and event["verb"].startswith("note.")
]
assert {event["verb"] for event in note_events} >= {"note.created", "note.updated"}
```

Silme testinde günlükten `note.deleted` beklemek yerine global aktivitede kaldığını doğrula:

```python
assert not any(
    event["verb"].startswith("note.")
    for group in journal
    for event in group["events"]
)
activity = (await client.get("/api/activity", params={"limit": 100})).json()
assert any(event["verb"] == "note.deleted" for event in activity)
```

- [ ] **Step 2: Testin doğru nedenle düştüğünü doğrula**

Run:

```bash
docker compose -p forkos-test -f compose.yaml -f compose.test.yaml run --rm backend-test sh -c 'alembic upgrade head && pytest -q tests/test_project_journal.py'
```

Expected: Journal cevabında `note.created`/`note.updated` bulunduğu için FAIL.

- [ ] **Step 3: Backend birleştirmesini sadeleştir**

`journal()` içindeki `note_events` sorgusunu ve bu event'leri `event_rows` içine ekleyen döngüyü kaldır. Event birleşimi yalnız mevcut proje timeline'ından gelsin:

```python
project_events = await timeline(session, project_id, limit)
events = project_events[:limit]
```

Not sorgusu ve `notes_by_day` gruplaması aynen kalır; böylece not içeriği günlük cevabında yaşamaya devam eder.

- [ ] **Step 4: Backend hedef testlerini çalıştır**

Run:

```bash
docker compose -p forkos-test -f compose.yaml -f compose.test.yaml run --rm backend-test sh -c 'alembic upgrade head && pytest -q tests/test_project_journal.py tests/test_notes.py'
```

Expected: Tüm testler PASS.

---

### Task 2: Seçili günü tek birleşik çalışma yüzeyine dönüştür

**Files:**
- Modify: `frontend/src/modules/projects/ProjectJournal.test.tsx`
- Modify: `frontend/src/modules/projects/ProjectJournal.tsx`

**Interfaces:**
- Consumes: `ProjectJournalDay[]`, `VERB_LABELS`, mevcut `Input` ve `Textarea` primitive'leri.
- Produces: `visibleProjectEvents(events)`, `projectEventLabel(verb)` ve seçili gün için tek aktif kart.

- [ ] **Step 1: Failing frontend regresyon testlerini yaz**

Fixture'a aynı gün için `note.created`, bilinmeyen `custom.internal_event` ve bir önceki gün grubu ekle. Aşağıdaki davranışları doğrula:

```tsx
expect(screen.queryByText("note.created")).toBeNull();
expect(screen.queryByText("custom.internal_event")).toBeNull();
expect(screen.getByText("Proje hareketi")).toBeTruthy();
expect(screen.getAllByText("Eski günlük notu")).toHaveLength(1);

const active = screen.getByTestId("project-journal-active-day");
expect(within(active).getByText("Entegrasyonu tamamla")).toBeTruthy();
expect(screen.getByText("Geçmiş gün notu")).toBeTruthy();
```

Geçmiş gün düğmesine basınca aktif kartın tarihinin değiştiğini doğrula:

```tsx
fireEvent.click(screen.getByRole("button", { name: /28 Ağustos/ }));
expect(within(screen.getByTestId("project-journal-active-day")).getByDisplayValue("Geçmiş gün notu")).toBeTruthy();
```

- [ ] **Step 2: Testin mevcut tekrar ve teknik verb nedeniyle düştüğünü doğrula**

Run:

```bash
cd frontend && npm test -- --run src/modules/projects/ProjectJournal.test.tsx
```

Expected: `note.created` görünür, seçili not iki kez render edilir ve aktif yüzey test id'si yoktur.

- [ ] **Step 3: Event görünürlüğü ve etiket helper'larını ekle**

`ProjectJournal.tsx` içinde:

```tsx
export function visibleProjectEvents(events: ProjectEvent[]): ProjectEvent[] {
  return events.filter((event) => !event.verb.startsWith("note."));
}

export function projectEventLabel(verb: string): string {
  return VERB_LABELS[verb] ?? "Proje hareketi";
}
```

Event satırında `VERB_LABELS[event.verb] ?? event.verb` yerine `projectEventLabel(event.verb)` kullan. `entity_type` chip'ini ve `Chip` importunu kaldır.

- [ ] **Step 4: Aktif gün ve geçmiş grupları ayır**

```tsx
const activeGroup = groups.find((group) => group.day === selectedDay);
const activeEvents = visibleProjectEvents(activeGroup?.events ?? []);
const historyGroups = groups.filter((group) => group.day !== selectedDay);
```

Tarih seçiciyi kompakt tek satır araç çubuğuna taşı. Altında `data-testid="project-journal-active-day"` bulunan tek kartta tarih başlığı, 4 satırlık textarea ve `Günün hareketleri` listesi göster. Hareket yoksa `Bu gün henüz proje hareketi yok.` metni göster.

Geçmiş bölümünde yalnız `historyGroups` render et. Her kartın not önizlemesi ve `visibleProjectEvents(group.events)` listesi aynı kart içinde kalsın. Kart başlığına basmak `setSelectedDay(group.day)` çağırmalı.

- [ ] **Step 5: Frontend hedef testini ve formatı çalıştır**

Run:

```bash
cd frontend && npx prettier --write src/modules/projects/ProjectJournal.tsx src/modules/projects/ProjectJournal.test.tsx
cd frontend && npm test -- --run src/modules/projects/ProjectJournal.test.tsx
```

Expected: ProjectJournal testleri PASS, format temiz.

---

### Task 3: Tam doğrulama, commit ve GitHub main entegrasyonu

**Files:**
- Modify: `docs/superpowers/plans/2026-08-29-project-journal-refinement.md` yalnız plan kaydı olarak commit'e dahil edilir.

**Interfaces:**
- Consumes: Tam backend/frontend test ve build komutları.
- Produces: Doğrulanmış commit, güncel yerel `main`, GitHub `origin/main` push'u.

- [ ] **Step 1: Tam doğrulamayı çalıştır**

```bash
docker compose -p forkos-test -f compose.yaml -f compose.test.yaml run --rm backend-test sh -c 'alembic upgrade head && pytest -q'
docker compose -p forkos-test -f compose.yaml -f compose.test.yaml run --rm --no-deps backend-test ruff check app tests scripts
cd frontend && npm test && npm run build && npm run api:check && node scripts/check-endpoint-coverage.mjs
git diff --check
```

Expected: Backend ve frontend testleri PASS, build exit 0, OpenAPI güncel, referanssız uç 0, diff-check temiz.

- [ ] **Step 2: Uygulamayı commit et**

```bash
git add backend/app/modules/project/service.py backend/tests/test_project_journal.py frontend/src/modules/projects/ProjectJournal.tsx frontend/src/modules/projects/ProjectJournal.test.tsx docs/superpowers/plans/2026-08-29-project-journal-refinement.md
git commit -m "fix: unify project notes with journal timeline"
```

- [ ] **Step 3: Uzak main'i güvenli şekilde güncelle**

```bash
git fetch origin main
git checkout main
git pull --ff-only origin main
git merge --ff-only codex/fix-phase-28-35
git push origin main
```

Expected: Push başarılı, `origin/main` yeni implementation commit'inde ve çalışma ağacı temiz.
