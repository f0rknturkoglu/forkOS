# Opportunity Score and Capture Extension Design

## Goal

Finish the partially implemented opportunity scoring UI, make bookmark capture loss-safe, and install the unpacked extension in the local Chromium browser.

## Opportunity score

- Opportunity cards remain sorted by numeric score and show a compact score badge.
- The opportunity detail drawer shows only the numeric score, its band, and the progress bar.
- Score reason breakdowns are not rendered.
- The API may keep `score_reasons` for compatibility and future diagnostics, but the frontend does not consume it.
- Existing filters, including hiding killed opportunities, remain available.
- The duplicate `earning` label and any now-unused score-reason helpers are removed so TypeScript builds cleanly.

## Capture extension

- `enqueue()` writes every capture to local storage before attempting network delivery.
- Queue flushing is single-flight: alarm, startup, popup, keyboard shortcut, and context-menu triggers share one active flush operation.
- A flush removes only items whose `client_uuid` was acknowledged by the backend. Items added during a flush cannot be overwritten by an older queue snapshot.
- Network and server failures remain pending for retry.
- Unsupported non-HTTP(S) pages are rejected before enqueueing with a visible message.
- Backend `4xx` responses are surfaced as rejected captures rather than counted as successful saves.
- The unused `scripting` permission is removed.

## Testing

- Backend tests cover score extraction from both JSON strings and dictionaries.
- Frontend type/build verification covers the simplified score presentation.
- Extension tests reproduce concurrent flushing and rejected URL behavior before the fix, then verify that unsent records remain safe.
- The existing capture idempotency tests remain green.

## Installation and acceptance

- Load `extension/` as an unpacked extension in Brave Nightly.
- Record the installed extension ID in `.env` and recreate the API container.
- Confirm the extension service worker can reach the local health endpoint.
- Save one disposable HTTP(S) bookmark through the extension, verify it appears in forkOS, and remove the disposable bookmark afterward.

The implementation does not alter unrelated opportunity, notification, or source-picker work already present in the working tree.
