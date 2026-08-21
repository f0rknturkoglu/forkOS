# Glance Shell and Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the responsive two-level forkOS header, minimalist server indicator, shared flat UI primitives, and a genuine Glance-style Today dashboard without changing backend contracts.

**Architecture:** Add explicit structural primitives instead of changing `Panel` globally, extract registry-driven navigation into a focused header, and retain `ModuleSpec.todayWidgets` as the dashboard extension point. Today uses a small/full/small grid on desktop and deterministic content order on tablet/mobile.

**Tech Stack:** React 18, TypeScript 5.5, Tailwind CSS 3.4, TanStack Query 5, Vite 5, Vitest, React server rendering.

## Global Constraints

- Everything remains local-only; add no auth, tenant, or new backend behavior.
- Keep `frontend/src/modules/index.ts` as the sole module registration point.
- Preserve API paths, React Query keys, offline read-only behavior, and source failure alerts.
- Use semantic colors from `frontend/src/index.css`; do not hard-code Tailwind palette colors in JSX.
- Preserve light and dark themes; do not copy Glance or Ryot code.
- Treat every pre-existing dirty/untracked file as user-owned. Do not stash, reset, delete, or stage unrelated changes.
- Before committing, run `git diff --cached --name-only`. For overlapping dirty files, keep a verified working-tree checkpoint instead of capturing user work.
- Verify widths 375, 768, 1024, 1280, and 1600 px.

---

## File Map

- Create `frontend/src/core/ui.test.tsx`: structural primitive tests.
- Create `frontend/src/core/navigation.ts` and `navigation.test.ts`: pure navigation model and tests.
- Create `frontend/src/core/AppHeader.tsx`: two-level registry-driven header.
- Modify `frontend/package.json` and lockfile: Vitest command/dependency.
- Modify `frontend/src/core/ui.tsx`: flat structural primitives.
- Modify `frontend/src/index.css`: Glance tokens and dashboard grid.
- Modify `frontend/src/core/registry.ts`: navigation module export.
- Modify `frontend/src/core/ServerLed.tsx`: compact trigger, existing popover.
- Modify `frontend/src/app/App.tsx`: use `AppHeader`.
- Modify `frontend/src/modules/today/TodayPage.tsx`, `today/index.ts`, and `today/widgets/*.tsx`: responsive dashboard.
- Modify module-owned Today widget files listed in Task 5.

### Task 1: Test Harness and Flat UI Primitives

**Files:**
- Create: `frontend/src/core/ui.test.tsx`
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify: `frontend/src/core/ui.tsx`
- Modify: `frontend/src/index.css`

**Interfaces:**
- Consumes: existing `cx`, React `ReactNode`, and semantic Tailwind tokens.
- Produces: `PageFrame`, `PageHeader`, `Section`, `Surface`, `MetricStrip`, `Metric`, `Toolbar`, `RowList` from `@/core/ui`.

- [ ] **Step 1: Add Vitest**

Add `"test": "vitest run"` to scripts and `"vitest": "^2.1.9"` to devDependencies without changing existing entries.

Run: `cd frontend && npm install`

Expected: install exits 0 and the lockfile records Vitest.

- [ ] **Step 2: Write failing primitive tests**

Create `frontend/src/core/ui.test.tsx`:

```tsx
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { Metric, MetricStrip, PageFrame, RowList, Section, Surface, Toolbar } from "./ui";

describe("Glance UI primitives", () => {
  it("renders section content without a default card shell", () => {
    const html = renderToStaticMarkup(<Section title="RSS"><p>Akış</p></Section>);
    expect(html).toContain("RSS");
    expect(html).toContain("Akış");
    expect(html).not.toContain("rounded-card border border-subtle bg-surface");
  });

  it("keeps explicit surfaces, metrics, toolbars, and divided rows", () => {
    const html = renderToStaticMarkup(<PageFrame>
      <Surface><Toolbar>Filtre</Toolbar></Surface>
      <MetricStrip><Metric label="Açık" value={12} /></MetricStrip>
      <RowList>Satır</RowList>
    </PageFrame>);
    expect(html).toContain("max-w-[1600px]");
    expect(html).toContain("divide-x");
    expect(html).toContain("divide-y");
  });
});
```

- [ ] **Step 3: Verify the tests fail**

Run: `cd frontend && npm test -- src/core/ui.test.tsx`

Expected: FAIL because the new exports do not exist.

- [ ] **Step 4: Implement the primitives**

Add to `frontend/src/core/ui.tsx`:

```tsx
export function PageFrame({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cx("mx-auto w-full max-w-[1600px] px-4 py-5 sm:px-5 lg:px-6", className)}>{children}</div>;
}

export function PageHeader({ eyebrow, title, action }: { eyebrow?: ReactNode; title: ReactNode; action?: ReactNode }) {
  return <header className="flex flex-wrap items-end justify-between gap-3">
    <div>{eyebrow && <p className="label-caps">{eyebrow}</p>}<h1 className="mt-1 font-serif text-title text-primary">{title}</h1></div>
    {action}
  </header>;
}

export function Section({ title, hint, action, children, className, bodyClassName }: {
  title?: ReactNode; hint?: ReactNode; action?: ReactNode; children: ReactNode;
  className?: string; bodyClassName?: string;
}) {
  return <section className={className}>
    {(title || hint || action) && <header className="mb-2.5 flex min-h-5 items-center gap-3">
      {title && <h2 className="label-caps shrink-0 text-secondary">{title}</h2>}
      <span className="h-px min-w-4 flex-1 bg-subtle" />
      {hint && <span className="text-meta text-muted">{hint}</span>}
      {action}
    </header>}
    <div className={bodyClassName}>{children}</div>
  </section>;
}

export function Surface({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cx("rounded-card border border-subtle bg-surface", className)}>{children}</div>;
}

export function MetricStrip({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cx("grid divide-x divide-subtle border-y border-subtle", className)}>{children}</div>;
}

export function Metric({ label, value, hint }: { label: ReactNode; value: ReactNode; hint?: ReactNode }) {
  return <div className="min-w-0 px-3 py-2.5 first:pl-0 last:pr-0 sm:px-4">
    <div className="numeral truncate text-[24px] leading-none text-primary">{value}</div>
    <div className="mt-1 truncate text-meta text-secondary">{label}</div>
    {hint && <div className="truncate text-meta text-muted">{hint}</div>}
  </div>;
}

export function Toolbar({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cx("flex flex-wrap items-center gap-2 border-y border-subtle py-2.5", className)}>{children}</div>;
}

export function RowList({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cx("divide-y divide-subtle border-y border-subtle", className)}>{children}</div>;
}
```

Tune only the dark semantic values in `frontend/src/index.css`:

```css
[data-theme="dark"] {
  --canvas: #121214;
  --surface: #17171A;
  --surface-sunken: #1E1E22;
  --surface-hover: #202025;
  --border: #29292F;
  --border-strong: #3A3942;
  --accent: #D5B66F;
  --accent-surface: #272318;
  --accent-border: #453B24;
}
```

- [ ] **Step 5: Verify and checkpoint**

Run: `cd frontend && npm test -- src/core/ui.test.tsx && npm run build`

Expected: tests PASS and build exits 0.

Run: `git diff --check -- frontend/package.json frontend/package-lock.json frontend/src/core/ui.tsx frontend/src/core/ui.test.tsx frontend/src/index.css`

Expected: no output. Stage only attributable hunks; suggested safe commit is `Add flat Glance UI primitives`.

### Task 2: Pure Registry-Driven Navigation Model

**Files:**
- Create: `frontend/src/core/navigation.ts`
- Create: `frontend/src/core/navigation.test.ts`
- Modify: `frontend/src/core/registry.ts`

**Interfaces:**
- Consumes: `ModuleSpec`, `ModuleGroup`, `MODULE_GROUPS`, `enabledModules()`.
- Produces: `NavigationGroup`, `navigationGroups`, `activeNavigationGroup`, `groupTarget`, `navigationModules`.

- [ ] **Step 1: Write failing navigation tests**

Create `frontend/src/core/navigation.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import type { ModuleSpec } from "./types";
import { activeNavigationGroup, groupTarget, navigationGroups } from "./navigation";

const Page = () => null;
const modules: ModuleSpec[] = [
  { id: "today", title: "Bugün", group: "pinned", routes: [{ path: "/", element: Page }] },
  { id: "rss", title: "RSS", group: "capture", routes: [{ path: "/rss", element: Page }] },
  { id: "opportunity", title: "Fırsatlar", group: "track", routes: [
    { path: "/opportunities", element: Page }, { path: "/sources", element: Page },
  ] },
];

describe("navigation model", () => {
  const groups = navigationGroups(modules);
  it("derives the active group from secondary routes", () => {
    expect(activeNavigationGroup("/sources", groups).id).toBe("track");
  });
  it("uses the first module route as group target", () => {
    expect(groupTarget(groups.find((group) => group.id === "capture")!)).toBe("/rss");
  });
});
```

- [ ] **Step 2: Verify the test fails**

Run: `cd frontend && npm test -- src/core/navigation.test.ts`

Expected: FAIL because `navigation.ts` does not exist.

- [ ] **Step 3: Implement the navigation model**

Create `frontend/src/core/navigation.ts`:

```ts
import { MODULE_GROUPS } from "./types";
import type { ModuleGroup, ModuleSpec } from "./types";

export interface NavigationGroup { id: ModuleGroup; label: string; modules: ModuleSpec[] }

export function navigationGroups(modules: ModuleSpec[]): NavigationGroup[] {
  const pinned = modules.filter((module) => module.group === "pinned");
  const grouped = MODULE_GROUPS.map((group) => ({
    ...group,
    modules: modules.filter((module) => (module.group ?? "system") === group.id),
  })).filter((group) => group.modules.length > 0);
  return [{ id: "pinned", label: "Bugün", modules: pinned }, ...grouped];
}

export function activeNavigationGroup(path: string, groups: NavigationGroup[]): NavigationGroup {
  return groups.find((group) => group.modules.some((module) => module.routes.some((route) => route.path === path))) ?? groups[0];
}

export function groupTarget(group: NavigationGroup): string {
  return group.modules[0]?.routes[0]?.path ?? "/";
}
```

Add to `registry.ts`:

```ts
export const navigationModules = (): ModuleSpec[] => enabledModules();
```

- [ ] **Step 4: Verify and checkpoint**

Run: `cd frontend && npm test -- src/core/navigation.test.ts && npm run build`

Expected: PASS and build exits 0. Stage only `navigation*` and the isolated registry export; suggested commit is `Add registry-driven navigation model`.

### Task 3: Two-Level Header and Server Indicator

**Files:**
- Create: `frontend/src/core/AppHeader.tsx`
- Modify: `frontend/src/core/ServerLed.tsx`
- Modify: `frontend/src/app/App.tsx`

**Interfaces:**
- Consumes: Task 2 navigation model, `navigationModules`, command palette, notification panel, theme hook, `ServerLed`.
- Produces: `AppHeader({ path }: { path: string })`.

- [ ] **Step 1: Create `AppHeader`**

Implement `frontend/src/core/AppHeader.tsx` with the existing imports for `Search`, `Sun`, `Moon`, `NotificationPanel`, `ServerLed`, `Kbd`, theme helpers, and command palette. Use these complete component bodies:

```tsx
export function AppHeader({ path }: { path: string }) {
  const groups = navigationGroups(navigationModules());
  const activeGroup = activeNavigationGroup(path, groups);
  return <header className="shrink-0 border-b border-subtle bg-canvas/95 backdrop-blur">
    <div className="mx-auto flex h-12 w-full max-w-[1600px] items-center gap-3 px-4 sm:px-5 lg:px-6">
      <a href="#/" className="flex shrink-0 items-center gap-2" aria-label="forkOS Bugün">
        <span className="flex h-5 w-5 items-center justify-center rounded-sm bg-primary font-serif text-[13px] text-canvas">f</span>
        <span className="hidden font-serif text-[17px] text-primary sm:inline">forkOS</span>
      </a>
      <nav aria-label="Ana bölümler" className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto">
        {groups.map((group) => <a key={group.id} href={`#${groupTarget(group)}`} aria-current={group.id === activeGroup.id ? "page" : undefined}
          className={cx("shrink-0 px-2 py-1 text-meta", group.id === activeGroup.id ? "text-primary" : "text-muted hover:text-primary")}>{group.label}</a>)}
      </nav>
      <div className="flex shrink-0 items-center gap-2"><ServerLed /><HeaderUtilities /></div>
    </div>
    <nav aria-label="Modüller" className="border-t border-subtle/70">
      <div className="mx-auto flex h-9 w-full max-w-[1600px] items-center gap-4 overflow-x-auto px-4 sm:px-5 lg:px-6">
        {activeGroup.modules.map((module) => <ModuleTab key={module.id} module={module} path={path} />)}
      </div>
    </nav>
  </header>;
}

function ModuleTab({ module, path }: { module: ModuleSpec; path: string }) {
  const target = module.routes[0]?.path ?? "/";
  const active = module.routes.some((route) => route.path === path);
  return <a href={`#${target}`} aria-current={active ? "page" : undefined}
    className={cx("flex h-9 shrink-0 items-center border-b-2 text-meta", active ? "border-accent text-primary" : "border-transparent text-muted hover:text-primary")}>{module.title}</a>;
}

function HeaderUtilities() {
  const [theme, setTheme] = useTheme();
  return <>
    <button type="button" onClick={openCommandPalette}
      className="hidden h-8 w-52 items-center gap-2 border-b border-subtle px-1 text-left text-meta text-muted hover:border-strong xl:flex">
      <Search size={14} /><span className="flex-1 truncate">Ara veya komut…</span><Kbd>Ctrl K</Kbd>
    </button>
    <button type="button" onClick={openCommandPalette} title="Ara (Ctrl+K)" aria-label="Ara"
      className="flex h-8 w-8 items-center justify-center text-muted hover:text-primary xl:hidden"><Search size={15} /></button>
    <NotificationPanel />
    <button type="button" onClick={() => setTheme(theme === "dark" ? "light" : "dark")} title="Temayı değiştir" aria-label="Temayı değiştir"
      className="flex h-8 w-8 items-center justify-center text-muted hover:text-primary">{theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}</button>
  </>;
}
```

Define `ModuleTab`, `HeaderUtilities`, and `ThemeToggle` in the same file using the current App implementations. Full search appears at `xl`; icon-only appears below `xl`.

- [ ] **Step 2: Flatten `ServerLed` trigger**

Keep all existing query, tone, bars, and popover code. Replace the trigger with:

```tsx
<button type="button" onClick={() => setOpen((value) => !value)} title="Yerel sunucu durumu"
  aria-expanded={open} className="flex h-8 items-center gap-1.5 px-1 text-meta text-muted hover:text-primary">
  <span className={cx("h-2 w-2 rounded-full", DOT[tone])} />
  <span className="hidden lg:inline">yerel</span>
</button>
```

- [ ] **Step 3: Wire `AppHeader` into App**

Import `AppHeader`, remove inline `Tab`, `NavBar`, and moved theme controls, and render:

```tsx
<div className="flex min-h-dvh flex-col bg-canvas text-primary">
  <AppHeader path={path} />
  <main className="min-h-0 min-w-0 flex-1">
    {!online && <Banner tone="warn" icon={<WifiOff size={15} />}>
      Çevrimdışısın. Kayıtlı veriler okunabilir, yazma işlemleri kapalı. Tarayıcı eklentisi kaydettiklerini kuyruğa alır.
    </Banner>}
    <SourceAlert />
    <Page />
  </main>
  <CommandPalette />
  <DialogHost />
</div>
```

Preserve settings hydration, `SourceAlert`, offline copy, dialogs, and query behavior.

- [ ] **Step 4: Verify header behavior**

Run: `cd frontend && npm test && npm run build`

Expected: PASS and build exits 0.

Inspect `/` at all acceptance widths. Primary/secondary rows must remain reachable; utilities must not leave the viewport; the server popover must still open. Suggested safe commit: `Build responsive two-level header`.

### Task 4: Responsive Today Layout and Today-Owned Widgets

**Files:**
- Modify: `frontend/src/modules/today/TodayPage.tsx`
- Modify: `frontend/src/modules/today/index.ts`
- Modify: `frontend/src/modules/today/widgets/*.tsx`
- Modify: `frontend/src/index.css`

**Interfaces:**
- Consumes: `allTodayStats`, `allTodayWidgetsIn`, Task 1 primitives, existing widget queries.
- Produces: desktop 300/flexible/300 grid, tablet main+rail, mobile metric/main/left/right order.

- [ ] **Step 1: Add explicit dashboard grid CSS**

```css
.dashboard-grid { display: grid; grid-template-areas: "main" "left" "right"; gap: 1.25rem; }
.dashboard-main { grid-area: main; min-width: 0; }
.dashboard-left { grid-area: left; min-width: 0; }
.dashboard-right { grid-area: right; min-width: 0; }
@media (min-width: 768px) and (max-width: 1279px) {
  .dashboard-grid { grid-template-columns: minmax(0, 1fr) 280px; grid-template-areas: "main left" "main right"; align-items: start; }
}
@media (min-width: 1280px) {
  .dashboard-grid { grid-template-columns: 300px minmax(0, 1fr) 300px; grid-template-areas: "left main right"; align-items: start; }
}
```

- [ ] **Step 2: Rebuild `TodayPage`**

Use `PageFrame className="dashboard-grid"`. Render main first in DOM order, then left/right asides. Main contains `<MetricStrip className="grid-cols-2 md:grid-cols-4">` and a single `space-y-5` widget flow; remove `todayColumns()` and the nested center grid. The fixed responsive class also supports stat components that return multiple `Metric` children through a fragment.

- [ ] **Step 3: Register owned widget slots**

Use:

```ts
todayWidgets: [
  { component: RssPanelWidget, zone: "rhythm", slot: "left" },
  { component: ClockWidget, zone: "rhythm", slot: "center" },
  { component: WeatherWidget, zone: "rhythm", slot: "right" },
  { component: ServerStatsWidget, zone: "rhythm", slot: "right" },
  { component: GithubReposWidget, zone: "rhythm", slot: "right" },
  { component: QuickLinksWidget, zone: "rhythm", slot: "right" },
]
```

- [ ] **Step 4: Flatten Today-owned widget shells**

Weather, GitHub, RSS, quick links, and server stats use `Section`; lists use `RowList`. Clock becomes a headerless `border-y border-subtle py-4 text-center` block. Preserve all queries/actions.

- [ ] **Step 5: Verify Today**

Run: `cd frontend && npm test && npm run build`

Expected: PASS. At 1280/1600 the layout is 300/flexible/300; at 768/1024 main+rail; at 375 metrics/main/left/right. Suggested safe commit: `Rebuild Today with responsive Glance layout`.

### Task 5: Module-Owned Today Widgets and Shell Regression

**Files:**
- Modify: `frontend/src/modules/activity/ActivityWidget.tsx`
- Modify: `frontend/src/modules/bookmarks/ReadingQueueWidget.tsx`
- Modify: `frontend/src/modules/calendar/TodayScheduleWidget.tsx`
- Modify: `frontend/src/modules/finance/RecurringWidget.tsx`
- Modify: `frontend/src/modules/habit/HabitWidget.tsx`
- Modify: `frontend/src/modules/health/HealthTodayWidget.tsx`
- Modify: `frontend/src/modules/inbox/InboxStats.tsx`
- Modify: `frontend/src/modules/inbox/InboxWidget.tsx`
- Modify: `frontend/src/modules/opportunity/OpportunityWidget.tsx`
- Modify: `frontend/src/modules/pomodoro/PomodoroWidget.tsx`
- Modify: `frontend/src/modules/rss/RssStats.tsx`
- Modify: `frontend/src/modules/study/StudyWidget.tsx`
- Modify: `frontend/src/modules/todo/PlannerWidget.tsx`
- Modify: `frontend/src/modules/todo/TodoWidget.tsx`
- Modify: corresponding module `index.ts` files.

**Interfaces:**
- Consumes: flat primitives and each widget's existing data hooks.
- Produces: every dashboard widget follows the same section/row/metric contract.

- [ ] **Step 1: Assign deterministic slots**

Use: left = calendar schedule and reading queue; center = inbox, todo, planner, pomodoro, opportunities, activity, study; right = habits, recurring payments, health. Preserve existing `zone` values.

- [ ] **Step 2: Convert stats and lists**

`InboxStats` and `RssStats` replace every existing `Stat` child with `Metric`; their fragments may continue to return two metric children. Convert `TodoWidget` to this exact outer structure while retaining its current query:

```tsx
<Section title="Bugünün görevleri" hint={`${visible.length} açık`} action={<button onClick={() => navigate("/todos")} className="text-meta text-muted hover:text-primary">tümünü aç →</button>}>
  {visible.length === 0 ? <Empty>Bugün için açık görev yok.</Empty> :
    <RowList>{visible.map((todo) => <div key={todo.id} className="flex min-w-0 items-center gap-2 py-2 text-body">
      <span className="h-2 w-2 rounded-full bg-accent" />
      <span className="truncate">{todo.title}</span>
      <span className="ml-auto text-[10.5px] text-muted">p{todo.priority}</span>
    </div>)}</RowList>}
</Section>
```

Preserve mutations and invalidation keys.

- [ ] **Step 3: Run full foundation verification**

Run:

```bash
cd frontend
npm test
npm run build
cd ..
git diff --check -- frontend
```

Expected: all tests PASS, build exits 0, no whitespace output, no page-level overflow at acceptance widths, and every enabled module is reachable through the header.

- [ ] **Step 4: Audit scope and checkpoint**

Run `git status --short`, `git diff --stat`, and `git diff --cached --name-only`. Confirm unrelated backend/docs changes remain untouched. Commit only safely isolated widget hunks with message `Unify Today widgets with flat dashboard language`; otherwise report overlapping files without staging them.
