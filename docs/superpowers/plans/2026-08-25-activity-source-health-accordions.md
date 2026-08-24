# Activity and Source Health Accordions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the activity heatmap and make source-health logs and daily activity history compact, accessible accordions.

**Architecture:** Add one controlled source-health disclosure under `frontend/src/core` and reuse it in Activity and Settings. Keep daily grouping in `ActivityPage`, with a local set of open day keys and one bulk toggle. Existing React Query endpoints and models remain unchanged.

**Tech Stack:** React 18, TypeScript, TanStack React Query, native `<details>/<summary>`, Vitest, Testing Library, Tailwind CSS.

## Global Constraints

- Keep all data local and add no backend endpoint.
- Preserve offline read-only behavior.
- Use existing design tokens and UI primitives.
- Keep disclosure state in React state; do not use `localStorage`.
- Use native disclosure semantics; color cannot be the only state signal.
- Write and observe each failing test before production code.

---

## File Map

- Create `frontend/src/core/SourceHealthAccordion.tsx`: shared controlled disclosure.
- Create `frontend/src/core/SourceHealthAccordion.test.tsx`: component behavior tests.
- Modify `frontend/src/modules/activity/ActivityPage.tsx`: remove heatmap and collapse timeline days.
- Create `frontend/src/modules/activity/ActivityPage.test.tsx`: activity behavior tests.
- Modify `frontend/src/modules/settings/SettingsPage.tsx`: consume shared disclosure.
- Create `frontend/src/modules/settings/SettingsSourceHealth.test.tsx`: Settings contract.

### Task 1: Shared Source Health Accordion

**Files:**
- Create: `frontend/src/core/SourceHealthAccordion.tsx`
- Create: `frontend/src/core/SourceHealthAccordion.test.tsx`

**Interfaces:**
- Consumes: `SourceHealth`, `Badge`, `Empty`, `cx`, `relativeTime`.
- Produces:

```ts
export interface SourceHealthAccordionProps {
  title?: string;
  sources: SourceHealth[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
}
export function SourceHealthAccordion(props: SourceHealthAccordionProps): JSX.Element;
```

- [ ] **Step 1: Write failing tests**

Create a jsdom test with one `ok` and one `error` run. Assert a closed render has no `open` attribute but shows `2 kayıt` and `1 sorunlu`. Render it open, dispatch a native `toggle` after setting `details.open = false`, and assert `onOpenChange(false)`. Also assert source name and error text are present when open.

Core test body:

```tsx
const onOpenChange = vi.fn();
const { container } = render(
  <SourceHealthAccordion sources={runs} open={false} onOpenChange={onOpenChange} />,
);
expect(container.querySelector("details")?.hasAttribute("open")).toBe(false);
expect(screen.getByText("2 kayıt")).toBeTruthy();
expect(screen.getByText("1 sorunlu")).toBeTruthy();
```

- [ ] **Step 2: Verify RED**

Run: `cd frontend && npm test -- --run src/core/SourceHealthAccordion.test.tsx`

Expected: FAIL because `SourceHealthAccordion` does not exist.

- [ ] **Step 3: Implement the minimal component**

Use a controlled native disclosure:

```tsx
<details
  data-source-health
  open={open}
  onToggle={(event) => onOpenChange(event.currentTarget.open)}
  className="overflow-hidden rounded-card border border-subtle bg-surface shadow-card"
>
  <summary className="flex cursor-pointer list-none items-center gap-3 px-4 py-3 marker:content-none">
    <ChevronDown className={cx("transition-transform", open && "rotate-180")} size={15} />
    <span className="text-body font-medium text-primary">{title}</span>
    <span className="ml-auto text-meta text-muted">{sources.length} kayıt</span>
    {healthy > 0 && <Badge tone="ok">{healthy} sağlıklı</Badge>}
    {problematic > 0 && <Badge tone="warn">{problematic} sorunlu</Badge>}
  </summary>
  <ul className="border-t border-subtle">
    {sources.map((source) => (
      <li key={source.id} className="grid gap-1 border-b border-subtle px-4 py-2.5 last:border-b-0 sm:grid-cols-[minmax(0,1fr)_auto_auto]">
        <div className="min-w-0">
          <p className="truncate text-body text-primary">{source.source}</p>
          {source.error && <p className="truncate text-meta text-danger">{source.error}</p>}
        </div>
        <Badge tone={source.status === "ok" ? "ok" : source.status === "error" ? "danger" : "warn"}>{source.status}</Badge>
        <span className="text-meta text-muted">+{source.items_found} · {relativeTime(source.started_at)}</span>
      </li>
    ))}
  </ul>
</details>
```

Each row renders `source`, status badge, `+items_found`, `relativeTime(started_at)`, and a truncated error. For an empty list, render `<Empty>Kayıt yok.</Empty>` inside the opened body.

- [ ] **Step 4: Verify GREEN**

Run: `cd frontend && npm test -- --run src/core/SourceHealthAccordion.test.tsx && npm run build`

Expected: component tests PASS and build exits 0.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/core/SourceHealthAccordion.tsx frontend/src/core/SourceHealthAccordion.test.tsx
git commit -m "feat: add source health accordion"
```

### Task 2: Collapsible Activity Timeline

**Files:**
- Modify: `frontend/src/modules/activity/ActivityPage.tsx`
- Create: `frontend/src/modules/activity/ActivityPage.test.tsx`

**Interfaces:**
- Consumes: `SourceHealthAccordion` from `@/core/SourceHealthAccordion`.
- Produces: day disclosures marked `data-activity-day`, with newest day initially open.

- [ ] **Step 1: Write failing page tests**

Mock `useQuery`: return two events on separate dates for `queryKey[0] === "activity"` and one error source otherwise. Assert:

```tsx
const { container } = render(<ActivityPage />);
expect(screen.queryByText("Emek haritası")).toBeNull();
const days = [...container.querySelectorAll("details[data-activity-day]")];
expect(days).toHaveLength(2);
expect(days[0].hasAttribute("open")).toBe(true);
expect(days[1].hasAttribute("open")).toBe(false);
expect(container.querySelector("details[data-source-health]")?.hasAttribute("open")).toBe(false);
```

In a second test click `Tümünü genişlet`, assert both day disclosures are open, click `Tümünü daralt`, and assert both are closed.

- [ ] **Step 2: Verify RED**

Run: `cd frontend && npm test -- --run src/modules/activity/ActivityPage.test.tsx`

Expected: FAIL because the heatmap and static `Section` timeline still exist.

- [ ] **Step 3: Implement the page behavior**

- Remove the `Heatmap` import and render.
- Add `healthOpen` boolean state.
- Add `openDays: Set<string>` state.
- Derive `dayEntries`, `dayKeys`, and `allDaysOpen`.
- Use an effect to drop stale open keys and open the newest visible day only when no visible day remains open.
- Add one toolbar button which sets all visible keys when not all are open, otherwise sets an empty set.
- Replace the source warning box with the shared component, passing only `problems`.
- Replace each day `Section` with controlled `<details data-activity-day open={openDays.has(day)}>`.
- Put day label, movement count, alert count, and a chevron in the summary; keep the current timeline `<ul>` unchanged inside.

State update for one day:

```ts
function setDayOpen(day: string, open: boolean) {
  setOpenDays((current) => {
    const next = new Set(current);
    if (open) next.add(day); else next.delete(day);
    return next;
  });
}
```

- [ ] **Step 4: Verify GREEN**

Run: `cd frontend && npm test -- --run src/core/SourceHealthAccordion.test.tsx src/modules/activity/ActivityPage.test.tsx`

Expected: all focused tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/core/SourceHealthAccordion.tsx frontend/src/modules/activity/ActivityPage.tsx frontend/src/modules/activity/ActivityPage.test.tsx
git commit -m "feat: collapse activity history by day"
```

### Task 3: Settings Source Health Disclosure

**Files:**
- Modify: `frontend/src/modules/settings/SettingsPage.tsx`
- Create: `frontend/src/modules/settings/SettingsSourceHealth.test.tsx`

**Interfaces:**
- Consumes: `SourceHealthAccordion`.
- Produces:

```ts
export function SettingsSourceHealth({ sources }: { sources: SourceHealth[] }): JSX.Element;
```

- [ ] **Step 1: Write the failing wrapper test**

Render `SettingsSourceHealth` with one healthy and one error run. Assert its `details[data-source-health]` starts closed and `2 kayıt` is visible. Click the `Kaynak sağlığı` summary and assert the disclosure opens and both source names are available.

```tsx
const { container } = render(<SettingsSourceHealth sources={sources} />);
const details = container.querySelector("details[data-source-health]")!;
expect(details.hasAttribute("open")).toBe(false);
fireEvent.click(screen.getByText("Kaynak sağlığı"));
expect(details.hasAttribute("open")).toBe(true);
```

- [ ] **Step 2: Verify RED**

Run: `cd frontend && npm test -- --run src/modules/settings/SettingsSourceHealth.test.tsx`

Expected: FAIL because `SettingsSourceHealth` is not exported.

- [ ] **Step 3: Implement the wrapper and replace the table**

```tsx
export function SettingsSourceHealth({ sources }: { sources: SourceHealth[] }) {
  const [open, setOpen] = useState(false);
  return <SourceHealthAccordion sources={sources} open={open} onOpenChange={setOpen} />;
}
```

Import the shared component, replace the final always-visible `Panel title="Kaynak sağlığı"` table with `<SettingsSourceHealth sources={sources} />`, and remove unused table-only imports.

- [ ] **Step 4: Verify GREEN**

Run: `cd frontend && npm test -- --run src/core/SourceHealthAccordion.test.tsx src/modules/settings/SettingsSourceHealth.test.tsx && npm run build`

Expected: focused tests PASS and build exits 0.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/modules/settings/SettingsPage.tsx frontend/src/modules/settings/SettingsSourceHealth.test.tsx
git commit -m "feat: collapse settings source health logs"
```

### Task 4: Full Verification and Runtime Check

**Files:**
- Modify only the files above if verification exposes a regression.

**Interfaces:**
- Consumes: Tasks 1-3.
- Produces: verified bundle and live forkOS UI.

- [ ] **Step 1: Run the complete frontend suite**

Run: `cd frontend && npm test`

Expected: all active tests PASS; the pre-existing Task 5 media contract remains skipped.

- [ ] **Step 2: Run contract and build checks**

Run: `cd frontend && node scripts/generate-api.mjs --check && npm run build`

Expected: schema check and build exit 0.

- [ ] **Step 3: Check repository formatting**

Run: `git diff --check && git status --short`

Expected: no whitespace errors and only intentional changes.

- [ ] **Step 4: Restart and verify the live frontend**

```bash
docker compose restart web
docker compose ps web
curl -fsS http://127.0.0.1:5173/ | grep '<title>forkOS</title>'
```

Expected: web becomes healthy and serves `forkOS`.

- [ ] **Step 5: Commit only if verification required a final adjustment**

```bash
git add frontend/src/core/SourceHealthAccordion.tsx frontend/src/core/SourceHealthAccordion.test.tsx frontend/src/modules/activity/ActivityPage.tsx frontend/src/modules/activity/ActivityPage.test.tsx frontend/src/modules/settings/SettingsPage.tsx frontend/src/modules/settings/SettingsSourceHealth.test.tsx
git commit -m "fix: finalize collapsible system views"
```

If no adjustment was required, do not create an empty commit.
