# Glance Module Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate every forkOS module page to the approved flat, responsive Glance-inspired language after the shared shell and dashboard primitives work.

**Architecture:** Apply four page archetypes—stream/list, planning/hierarchy, settings/health, and media—using the shared `PageFrame`, `Section`, `Surface`, `MetricStrip`, `Metric`, `Toolbar`, and `RowList`. Preserve module data flows and mutations; change hierarchy and presentation, not API contracts.

**Tech Stack:** React 18, TypeScript 5.5, Tailwind CSS 3.4, TanStack Query 5, Vite 5, Vitest.

## Global Constraints

- Complete `2026-08-22-glance-shell-dashboard.md` first.
- Keep backend, schema, API paths, React Query keys, event behavior, and extension capture behavior unchanged.
- Preserve offline read-only behavior, semantic tokens, and both themes.
- Keep every module reachable through the registry header.
- Treat pre-existing dirty files as user-owned; do not stash, reset, delete, or indiscriminately stage them.
- Verify widths 375, 768, 1024, 1280, and 1600 px.
- Deep Ryot features are out of scope; the current media page only receives the shared forkOS language.

---

## File Map

- Stream/list: `InboxPage.tsx`, `BookmarksPage.tsx`, `RssPage.tsx`, `ActivityPage.tsx`, `DocumentsPage.tsx`.
- Planning/hierarchy: `TodoPage.tsx`, `WeeklyPlannerPage.tsx`, `CalendarPage.tsx`, `ProjectsPage.tsx`, `PomodoroPage.tsx`, `StudyPage.tsx`.
- Tracking: `OpportunityPage.tsx`, `OpportunityDetail.tsx`, `SourceHealthPage.tsx`, `SyncProgress.tsx`, `HabitPage.tsx`, `LearningPage.tsx`, `FinancePage.tsx`, `ReviewPage.tsx`.
- System: `SettingsPage.tsx`, `HealthPage.tsx`, `health/widgets/*.tsx`.
- Media: `MediaPage.tsx`.

### Task 1: Stream and Capture Pages

**Files:**
- Modify: `frontend/src/modules/inbox/InboxPage.tsx`
- Modify: `frontend/src/modules/bookmarks/BookmarksPage.tsx`
- Modify: `frontend/src/modules/rss/RssPage.tsx`
- Modify: `frontend/src/modules/activity/ActivityPage.tsx`
- Modify: `frontend/src/modules/documents/DocumentsPage.tsx`

**Interfaces:**
- Consumes: shared primitives and existing module hooks/mutations.
- Produces: consistent page header, toolbar, and divided-row hierarchy.

- [ ] **Step 1: Apply the common stream shell**

Replace every root `p-6`/`p-8` wrapper with `PageFrame className="space-y-5"`. Add these exact headers before each page's current metrics and controls:

```tsx
// InboxPage
<PageHeader eyebrow="Yakala" title="Gelen Kutusu" />
// BookmarksPage
<PageHeader eyebrow="Yakala" title="Yer İmleri" />
// RssPage
<PageHeader eyebrow="Yakala" title="RSS Okuyucu" />
// ActivityPage
<PageHeader eyebrow="Sistem" title="Etkinlik" />
// DocumentsPage
<PageHeader eyebrow="Yakala" title="Belgeler" />
```

Move each page's current search, filter, sort, and primary create/sync controls into one `Toolbar`, preserving their current callbacks and Turkish labels.

- [ ] **Step 2: Flatten item containers**

Wrap each current mapped list once with `RowList`. Change each mapped item's outer class to `group flex min-w-0 gap-3 px-1 py-3 transition hover:bg-surface-hover`; remove only its `rounded-card`, outer `border`, and `bg-surface` classes. Preserve Inbox keyboard handlers/ref indexes, RSS reader selection, bookmark collection actions, activity timeline markup, and Drive actions. Selected rows use `bg-accent-surface`; ordinary rows have no card border/radius.

- [ ] **Step 3: Keep real panes bounded**

RSS reader detail, capture/edit forms, and destructive flows remain bounded. Replace their current outer `Panel` with `<Surface className="min-h-0 overflow-hidden">`, retaining the children verbatim. Do not wrap the surrounding list in another surface.

- [ ] **Step 4: Verify and checkpoint**

Run: `cd frontend && npm test && npm run build`

Expected: PASS. Inspect `#/inbox`, `#/bookmarks`, `#/rss`, `#/activity`, `#/documents` at all acceptance widths. Confirm no page overflow and all interactions remain functional.

Run `git diff --check` for Task 1 paths. Commit only isolated hunks with message `Flatten capture and stream pages`; leave overlapping user changes unstaged.

### Task 2: Planning and Hierarchy Pages

**Files:**
- Modify: `frontend/src/modules/todo/TodoPage.tsx`
- Modify: `frontend/src/modules/todo/WeeklyPlannerPage.tsx`
- Modify: `frontend/src/modules/calendar/CalendarPage.tsx`
- Modify: `frontend/src/modules/projects/ProjectsPage.tsx`
- Modify: `frontend/src/modules/pomodoro/PomodoroPage.tsx`
- Modify: `frontend/src/modules/study/StudyPage.tsx`

**Interfaces:**
- Consumes: shared primitives and existing drag, timer, navigation, selection, and mutation behavior.
- Produces: responsive split-pane/column layouts separated by hairlines.

- [ ] **Step 1: Apply PageFrame and one toolbar**

Use the Task 1 header shell. Put create, date navigation, and mode controls in one `Toolbar`; do not create a separate card for a single form row.

- [ ] **Step 2: Replace planning cards with bounded columns**

For three-region pages, set the current outer grid to `grid min-w-0 divide-y divide-subtle border-y border-subtle lg:grid-cols-[minmax(220px,0.7fr)_minmax(0,1.6fr)_minmax(260px,0.9fr)] lg:divide-x lg:divide-y-0`. Set current left/main/detail wrappers respectively to `min-w-0 py-3 lg:pr-4`, `min-w-0 py-3 lg:px-4`, and `min-w-0 py-3 lg:pl-4`. Use the matching two-column subset for two-region pages. Mobile DOM order is list/main, then detail/support. Selected and drag-target states retain surface color.

- [ ] **Step 3: Flatten Todo and Pomodoro**

Todo items use `RowList`; completed/dropped states remain muted. Pomodoro's active timer is a deliberate `Surface`, while history and presets are flat `Section`s. Preserve timer lifecycle and URL context.

- [ ] **Step 4: Verify and checkpoint**

Run: `cd frontend && npm test && npm run build`

Expected: PASS. Inspect `#/todos`, `#/planner`, `#/calendar`, `#/projects`, `#/pomodoro`, `#/study`; exercise drag/drop, selection, and timer controls.

Run `git diff --check` for Task 2 paths. Commit isolated hunks with message `Unify planning pages with responsive split layouts`.

### Task 3: Tracking and Opportunity Pages

**Files:**
- Modify: `frontend/src/modules/opportunity/OpportunityPage.tsx`
- Modify: `frontend/src/modules/opportunity/OpportunityDetail.tsx`
- Modify: `frontend/src/modules/opportunity/SourceHealthPage.tsx`
- Modify: `frontend/src/modules/opportunity/SyncProgress.tsx`
- Modify: `frontend/src/modules/habit/HabitPage.tsx`
- Modify: `frontend/src/modules/learning/LearningPage.tsx`
- Modify: `frontend/src/modules/finance/FinancePage.tsx`
- Modify: `frontend/src/modules/review/ReviewPage.tsx`

**Interfaces:**
- Consumes: opportunity trash/permanent-delete/sync behavior and shared primitives.
- Produces: score-first opportunity rows and consistent tracking sections.

- [ ] **Step 1: Consolidate Opportunity controls**

Wrap the current search, kind, status, sort, killed toggle, and live/trash controls in `<Toolbar className="sticky top-0 z-10 bg-canvas/95 backdrop-blur">`. Insert `<span className="min-w-2 flex-1" />` immediately before the current `SourcePicker` and `SyncProgress` nodes so sync controls align right on wide screens. Filter subgroups may scroll horizontally on mobile.

- [ ] **Step 2: Replace opportunity cards with score-first rows**

Use `RowList`. Each row displays score, title/organization, deadline, status, and contextual actions. Preserve trash, restore, permanent delete, sorting, paging, and navigation. Do not display score reason text.

- [ ] **Step 3: Flatten detail and source health**

Requirements, score, notes, and source sync become `Section`s. Keep destructive operations in a danger-token `Surface`. `SyncProgress` remains a compact progress row.

- [ ] **Step 4: Convert remaining tracking modules**

Habit heatmap, learning library/queues, finance tables/forms, and review summaries use `PageFrame`, `MetricStrip`, `Toolbar`, `Section`, `RowList`. Cover/tile media can keep aspect-ratio surfaces; metadata must not receive a second outer card.

- [ ] **Step 5: Verify and checkpoint**

Run: `cd frontend && npm test && npm run build`

Expected: PASS. Verify opportunity live/trash, restore/permanent delete, source sync, habit logging, learning progress, finance creation, and review navigation.

Run `git diff --check` for Task 3 paths. Commit isolated hunks with message `Flatten opportunity and tracking pages`.

### Task 4: Settings and Health Pages

**Files:**
- Modify: `frontend/src/modules/settings/SettingsPage.tsx`
- Modify: `frontend/src/modules/health/HealthPage.tsx`
- Modify: `frontend/src/modules/health/widgets/BackupHealthWidget.tsx`
- Modify: `frontend/src/modules/health/widgets/RssHealthWidget.tsx`
- Modify: `frontend/src/modules/health/widgets/SourceHealthWidget.tsx`

**Interfaces:**
- Consumes: settings persistence, integration state, backup/restore, health queries.
- Produces: semantic setting rows and flat status sections.

- [ ] **Step 1: Convert settings into sections and rows**

Wrap the page in `PageFrame`. Add this local helper above `SettingsPage` and use it for module, widget order, weather, integration, media link, backup, and restore controls:

```tsx
function SettingRow({ label, description, children }: { label: string; description?: string; children: React.ReactNode }) {
  return <div className="grid gap-2 border-b border-subtle py-3 last:border-b-0 md:grid-cols-[minmax(180px,0.7fr)_minmax(0,1.3fr)] md:items-center">
    <div><p className="text-body text-primary">{label}</p>{description && <p className="text-meta text-muted">{description}</p>}</div>
    <div className="min-w-0 md:justify-self-end">{children}</div>
  </div>;
}
```

Keep module toggles, widget order, weather, integrations, media links, backup, restore, and source health behavior unchanged. Remove the visible `today.columns` selector because Task 4 of the foundation plan replaces the nested center grid; leave the stored backend setting untouched for backward compatibility.

- [ ] **Step 2: Flatten health widgets**

Health uses a responsive two-column grid of `Section`s. Status entries are divided rows. Backup restore/destructive actions remain bounded by `Surface`.

- [ ] **Step 3: Verify and checkpoint**

Run: `cd frontend && npm test && npm run build`

Expected: PASS. Inspect `#/settings` and `#/health` in both themes and all widths. Exercise module toggles, integrations, backup, restore confirmation, and error states.

Run `git diff --check` for Task 4 paths. Commit isolated hunks with message `Rework settings and health into flat sections`.

### Task 5: Media Shared-Language Migration

**Files:**
- Modify: `frontend/src/modules/media/MediaPage.tsx`

**Interfaces:**
- Consumes: `/media`, `/media/stats`, `/media/search`, create/update/delete mutations, external links, shared primitives.
- Produces: responsive media toolbar, metric strip, cover rows, expandable editor.

- [ ] **Step 1: Replace header badges with metrics**

```tsx
<MetricStrip className="grid-cols-2 sm:grid-cols-4">
  <Metric label="Toplam" value={stats?.total ?? 0} />
  <Metric label="Devam ediyor" value={stats?.in_progress ?? 0} />
  <Metric label="Tamamlandı" value={stats?.completed ?? 0} />
  <Metric label="Planlandı" value={stats?.planned ?? 0} />
</MetricStrip>
```

- [ ] **Step 2: Merge search and filters**

Place kind/status filters, search-kind, metadata search, and add controls in one `Toolbar`. Search results open in a `Surface` below it. Quick external sites are a compact inline link row.

- [ ] **Step 3: Convert cards to cover rows**

```tsx
<RowList>{items.map((item) => {
  const open = expanded === item.id;
  const progressPct = item.total ? Math.min(100, Math.round(((item.progress ?? 0) / item.total) * 100)) : null;
  return <article key={item.id} className="grid min-w-0 grid-cols-[48px_minmax(0,1fr)] gap-3 py-3 sm:grid-cols-[64px_minmax(0,1fr)_auto]">
    <Cover url={String(item.meta?.cover_url ?? "") || null} title={item.title} size="h-20 w-12 sm:h-24 sm:w-16" />
    <div className="min-w-0">
      <button type="button" onClick={() => setExpanded(open ? null : item.id)} className="block w-full text-left text-body font-medium text-primary">{item.title}</button>
      <div className="mt-1 flex flex-wrap items-center gap-2 text-meta text-muted">
        <Badge>{KIND_LABELS[item.kind] ?? item.kind}</Badge>
        <Badge>{STATUS_LABELS[item.status] ?? item.status}</Badge>
        {item.score !== null && <span>{item.score}/10</span>}
        {progressPct !== null && <span>{item.progress}/{item.total}</span>}
      </div>
      {item.notes && !open && <p className="mt-1 line-clamp-1 text-meta text-secondary">{item.notes}</p>}
    </div>
    <div className="col-span-2 flex flex-wrap items-start gap-2 sm:col-span-1 sm:justify-end">
      {externalLinks(item, item.title).slice(0, 2).map(([name, url]) => <a key={name} href={url} target="_blank" rel="noreferrer" className="text-meta text-accent">{name} ↗</a>)}
      <Button size="sm" variant="danger" disabled={!online} onClick={() => confirmRemove(item)}><Trash2 size={12} /></Button>
    </div>
    {open && <div className="col-span-full border-t border-subtle pt-3"><MediaEditor item={item} onSave={(body) => update.mutate({ id: item.id, body })} /></div>}
  </article>;
})}</RowList>
```

Preserve types, filters, links, score, progress, edit, delete. On mobile, secondary actions wrap below metadata instead of forcing overflow.

- [ ] **Step 4: Verify and checkpoint**

Run: `cd frontend && npm test && npm run build`

Expected: PASS. Verify metadata search, add, filters, progress/score editing, external links, deletion, empty state, mobile layout.

Run `git diff --check -- frontend/src/modules/media/MediaPage.tsx`. Commit isolated hunks with message `Align media library with global forkOS language`.

### Task 6: Whole-Application Verification

**Files:**
- Modify only files that fail the checks below.

**Interfaces:**
- Consumes: both implementation plans.
- Produces: verified routes, themes, states, accessibility, and build.

- [ ] **Step 1: Run automated checks**

Run:

```bash
cd frontend
npm test
npm run build
cd ..
git diff --check -- frontend
```

Expected: all tests PASS, build exits 0, diff check prints nothing.

- [ ] **Step 2: Open every registry route through the header**

Required routes: `/`, `/inbox`, `/bookmarks`, `/rss`, `/activity`, `/todos`, `/planner`, `/pomodoro`, `/habits`, both review routes, `/opportunities`, `/sources`, `/study`, `/learning`, `/media`, `/documents`, `/calendar`, `/projects`, `/finance`, `/settings`, `/health`.

Expected: correct active group/module and no inaccessible route.

- [ ] **Step 3: Run responsive/theme matrix**

At 375, 768, 1024, 1280, and 1600 px inspect Today plus `/rss`, `/planner`, `/opportunities`, `/settings`, `/media` in light and dark themes.

Expected: no page-level horizontal overflow, stable utilities, correct dashboard transitions, readable primary actions.

- [ ] **Step 4: Verify state variants**

Check loading, empty, offline, source failure, sync-running, trash, destructive confirmation, server popover, command palette, notification panel, and focus-visible states.

Expected: overlays do not clip; focus remains visible; state variants do not reintroduce nested cards.

- [ ] **Step 5: Audit final scope**

Run:

```bash
git status --short
git diff --stat
git diff --name-only
git diff --cached --name-only
```

Expected: unrelated backend and user docs remain untouched. Commit only safely isolated UI hunks with message `Complete responsive Glance interface redesign`; otherwise report overlapping paths without forcing a commit.
