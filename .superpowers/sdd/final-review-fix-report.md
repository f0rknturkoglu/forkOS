# Final review fix evidence

## Scope

Fixed the final-review findings for the collapsible system views:

- Source-health summaries count every non-`ok` status as problematic.
- Activity's alert-only filter shares the `isAlert` predicate used by its alert display.
- Activity day state and grouping use a local `YYYY-MM-DD` key, while the Turkish label remains presentation-only.
- Added coverage for alert-filter state transitions and individual native disclosure toggles.

## RED (tests first)

Added the new fixtures and behavior tests before changing production code, then ran:

```sh
cd frontend
npm test -- --run src/core/SourceHealthAccordion.test.tsx src/modules/activity/ActivityPage.test.tsx
```

Result: exit 1; 2 test files failed, 3 tests failed, 5 tests passed. The expected failures were:

1. Source-health summary rendered `1 sorunlu` instead of `2 sorunlu` when an `empty` source was included.
2. `source_sync.completed` with `{ errors: 2 }` disappeared under `Sadece uyarılar`.
3. Events on 25 August in 2015 and 2026 rendered as one disclosure because their Turkish display label was identical.

The native disclosure test initially used a nonexistent `fireEvent.toggle` helper. It was corrected to dispatch the browser's `toggle` event directly; that test verifies existing native-toggle wiring rather than a newly introduced production behavior.

## GREEN

Production changes:

- `SourceHealthAccordion` now derives `problematic` with `status !== "ok"`.
- `ActivityPage` filters alert-only events with `isAlert`.
- `ActivityPage` groups by `localDayKey()` (`YYYY-MM-DD` from the local `Date`) and stores separate display labels via `dayLabel()`.
- All disclosure keys and `openDays` operations use the stable local key.

Focused verification (exit 0):

```sh
npm test -- --run src/core/SourceHealthAccordion.test.tsx src/modules/activity/ActivityPage.test.tsx
```

Output: 2 test files passed; 8 tests passed.

An initial build exposed a TypeScript-only test-helper narrowing issue for `payload.errors`. The helper was typed as `ActivityEvent`, then all checks were rerun fresh:

```sh
npm test -- --run src/core/SourceHealthAccordion.test.tsx src/modules/activity/ActivityPage.test.tsx
npm test
npm run build
```

Final output: focused 2/2 files and 8/8 tests passed; full suite 27 passed, 1 skipped files and 68 passed, 9 skipped tests; production build exited 0 and bundle check reported 1 entry chunk within limit and 72 assets generated.

## Files changed

- `frontend/src/core/SourceHealthAccordion.tsx`
- `frontend/src/core/SourceHealthAccordion.test.tsx`
- `frontend/src/modules/activity/ActivityPage.tsx`
- `frontend/src/modules/activity/ActivityPage.test.tsx`
- `.superpowers/sdd/final-review-fix-report.md`

## Self-review

- Confirmed all grouping, React keys, disclosure state, bulk expand/collapse, and filter-transition cleanup use the stable key rather than the display label.
- Confirmed the source-health summary now aligns with Activity's non-`ok` problem selection.
- Confirmed the failed-sync alert case is covered at the rendered filter behavior, not only by a predicate unit test.
- Ran `git diff --check` successfully.

## Concerns

No outstanding concerns. The local calendar key intentionally follows the browser's local timezone, matching the requested local day semantics.
