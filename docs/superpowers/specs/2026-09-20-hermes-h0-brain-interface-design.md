# forkOS × Hermes — H0: Brain Interface Foundation Specification

**Status:** Approved Architecture Design  
**Date:** 2026-09-20  
**Phase:** H0 (Brain Interface Foundation)  
**Authors:** forkOS Team & Agent  

---

## 1. Executive Summary & Core Philosophy

**forkOS × Hermes — H0** establishes the first agent-facing "brain interface" for forkOS + f0rknbrain.

The mental model is:
```text
                    Hermes (or Claude / MCP Client)
                                  │
                                  │ Streamable HTTP (MCP)
                                  ▼
                         ┌─────────────────┐
                         │ Brain Interface │
                         │     H0 MCP      │
                         └────────┬────────┘
                                  │
             ┌────────────────────┴────────────────────┐
             │                                         │
             ▼                                         ▼
          forkOS                                  f0rknbrain
    Operational State                          Knowledge Vault
 (Today, Todos, Projects,                  (Notes, Daily, Decisions,
  Activity, Deadlines...)                    Research, Learning...)
```

### Inviolable Principles of H0:
1. **Zero Mutation:** H0 exposes exactly **zero mutating tools**. No creating tasks, updating projects, completing items, writing to the Vault, or deleting data.
2. **Read-Only Observation Only:** H0 exists to prove that Hermes can observe, orient, and synthesize context cleanly before any action execution (H1) is permitted.
3. **No Second Shadow System:** H0 does not replicate forkOS data into a vector DB, does not mirror Vault markdown into PostgreSQL, and does not maintain duplicate persistent cache stores.
4. **Local-Only & Private:** Bounded to `127.0.0.1`. No external network calls (no OpenAI, no Anthropic, no telemetry, no GitHub remote refresh, no scraping). Zero credentials or private paths exposed.
5. **No Independent Pollers/Watchers:** The interface is pull-based. Idle when not in use.

---

## 2. Ownership Boundaries (Phase 3 Preserved)

| Domain | Owner | Storage / Format | H0 Interaction |
| :--- | :--- | :--- | :--- |
| **Operational State** (Today, Todos, Planner, Projects, Milestones, Deadlines, Flashcard counts, CRM, RSS items, Activity) | **forkOS** | PostgreSQL (`lifeos` / `forkos`) | Read-only service queries via `app.integrations.agent.context` |
| **Durable Knowledge** (Long-term notes, daily journals, project notes, research, decisions, source analyses) | **f0rknbrain** | Local Markdown Vault (`*.md` + YAML frontmatter) | Safe direct lexical scan and reader via `app.integrations.agent.knowledge` |
| **Hot Memory** (`90 Agent/Profile.md`, `Goals.md`, `Constraints.md`) | Future H2 | Future Vault directory | **Out of scope for H0**. Not created or read by H0. |
| **Legacy Notes Archive** (`note`, `note_folder`, `note_attachment`) | **Frozen Archive** | PostgreSQL archive tables | **Untouched**. Excluded from operational search. |

---

## 3. Architecture & Transport Specification

### 3.1 Single Canonical Transport: Streamable HTTP mounted in FastAPI
- **Protocol:** Model Context Protocol (MCP) Streamable HTTP transport using official `mcp>=1.0,<3.0` Python SDK.
- **Server Identity:** `forkos-brain`
- **Mount Point:** Mounted inside the existing FastAPI app at `/mcp`.
- **Address:** `http://127.0.0.1:8787/mcp` (loopback only, protected by `BIND_ADDR=127.0.0.1`).
- **Lifespan Integration:**
  - The `MCPServer` instance lazily creates a `StreamableHTTPSessionManager`.
  - In `backend/app/main.py`, FastAPI's lifespan context manager wraps `server.session_manager.run()`.
  - Session manager tasks start on FastAPI startup and shut down cleanly on FastAPI termination.
- **Security Settings:**
  - `TransportSecuritySettings(enable_dns_rebinding_protection=False)` or explicit allowlist `["127.0.0.1", "localhost"]` to allow local HTTP client connections without header rejections.

### 3.2 Directory & Code Organization
```text
backend/app/integrations/agent/
├── __init__.py          # Exports server and router mount helper
├── models.py            # Bounded Pydantic models & response envelopes
├── context.py           # Read-only forkOS state aggregators (Today, Todo, Project, Activity)
├── knowledge.py         # Safe, direct lexical Vault scanner and bounded Markdown reader
├── tools.py             # Semantic MCP tool definitions and tool registration
└── mcp.py               # MCPServer instance, Starlette app factory, lifecycle binding
```

---

## 4. Benchmark & Knowledge Retrieval Strategy

### 4.1 Empirical Vault Measurement (2026-09-20)
Benchmarked against user's actual Obsidian Vault:
- **Total Markdown Files:** 27 files
- **Total Markdown Size:** ~49.8 KB
- **Filesystem Scan Time:** 0.68 ms
- **Direct Lexical Search Latency:** 5.53 ms

### 4.2 Architecture Choice: Direct On-Demand Lexical Scan
Given that the entire Vault is under 100 KB and searches complete in ~5ms:
- **No In-Memory Index Needed for H0:** Eliminates memory overhead and invalidation bugs completely.
- **Always 100% Live:** Instant reflection of user edits in Obsidian without file watchers or background pollers.
- **Stateless & Zero RAM Overhead:** Reads files on demand, releases memory immediately.
- **Safety Exclusions:** Strictly ignores `.git`, `.obsidian`, `.forkos-migration`, `.trash`, and attachment directories.
- **Deterministic Lexical Ranking:**
  1. Exact title match (frontmatter title / H1 / filename stem) -> Score: 100
  2. Title token match -> Score: 80
  3. Heading token match -> Score: 50
  4. Path match -> Score: 30
  5. Body token match -> Score: 10

---

## 5. Public MCP Tool Suite (8 High-Level Read-Only Tools)

Every tool has metadata `readOnlyHint=True` (or equivalent read-only annotations) and includes in its description:
`"Read-only. Does not modify forkOS or the Vault."`

### 1. `forkos_briefing`
- **Purpose:** Factual, bounded summary of the user's operational day.
- **Input:**
  - `day` (optional `str`, format `YYYY-MM-DD`): Target day. Defaults to forkOS local today (`local_today()`).
- **Output:**
  - `as_of`: ISO timestamp.
  - `day`: Target date.
  - `agenda`: Top scheduled/time-blocked items (limit 30).
  - `open_todos`: High-priority / active todos (limit 20).
  - `deadlines`: Upcoming deadlines within 7 days (limit 15).
  - `active_projects`: Top active projects with their `next_action` (limit 10).
  - `learning_due`: SRS flashcards due and active learning topics (limit 10).
  - `opportunity_attention`: Actionable career opportunities (limit 10).
  - `notifications`: Unread operational notifications (limit 10).
  - `vault_status`: Brief summary of Vault availability.
  - `truncated`: Boolean indicating if any collection reached bounds.

### 2. `forkos_search`
- **Purpose:** Search active operational entities across forkOS.
- **Input:**
  - `query` (`str`, 2–200 chars): Search keyword.
  - `entity_types` (optional `list[str]`): Filter by entity types (e.g. `["project", "todo", "opportunity", "learning_topic"]`). Excludes `note` and `note_folder`.
  - `limit` (optional `int`, default 10, max 30).
- **Output:**
  - `results`: List of `{ id, type, title, route, summary }`.
  - `truncated`: Boolean.

### 3. `forkos_entity_context`
- **Purpose:** Inspect identity, deep links, related entities, and recent activity for an operational entity UUID.
- **Input:**
  - `entity_id` (`str`, UUID): Target entity ID.
- **Output:**
  - `id`, `type`, `title`, `route`, `details` (bounded type-specific summary), `related_entities` (links/references), `recent_events` (last 5 events), `knowledge_ref` (Vault note pointer if linked).

### 4. `forkos_project_context`
- **Purpose:** Full operational context packet for a project.
- **Input:**
  - `project_id` (`str`, UUID): Project ID.
- **Output:**
  - `project`: Identity, status, `next_action`, tech stack, configured GitHub repo.
  - `milestones`: Active/pending milestones.
  - `todos`: Open todos linked to this project (limit 20).
  - `recent_activity`: Last 10 project events.
  - `deadlines`: Upcoming milestones/deadlines.
  - `knowledge`: Vault pointer only (`forkos_id`, `relative_path`, `title`, `available`). *Full note body is NOT returned automatically.*

### 5. `forkos_recent_activity`
- **Purpose:** Inspect sanitized append-only operational events.
- **Input:**
  - `since` (optional `str`, ISO timestamp or preset `"today"`, `"yesterday"`, `"7d"`, `"30d"`).
  - `entity_type` (optional `str`).
  - `verb` (optional `str`).
  - `limit` (optional `int`, default 30, max 100).
- **Output:**
  - `events`: List of `{ id, timestamp, verb, entity_id, entity_type, title, payload }`.
  - Sensitive tokens/passwords/paths sanitized.

### 6. `brain_status`
- **Purpose:** Health, connectivity, and statistics of f0rknbrain Vault knowledge retrieval.
- **Input:** None.
- **Output:**
  - `brain_interface_version`: `1`.
  - `configured`: Boolean.
  - `available`: Boolean.
  - `readable`: Boolean.
  - `writable`: Boolean (informational).
  - `vault_name`: String.
  - `total_markdown_files`: Integer.
  - `managed_files_count`: Integer.
  - `conflicts_count`: Integer.
  - `invalid_metadata_count`: Integer.

### 7. `brain_search`
- **Purpose:** Lexical, deterministic search across all safe Markdown files in the Vault (managed + unmanaged).
- **Input:**
  - `query` (`str`, 2–200 chars): Search term.
  - `scope` (optional `str`, enum: `"all"`, `"inbox"`, `"daily"`, `"projects"`, `"knowledge"`, `"learning"`, `"career"`, `"sources"`).
  - `limit` (optional `int`, default 8, max 20).
- **Output:**
  - `results`: List of `{ locator, title, relative_path, forkos_id, forkos_type, matched_heading, snippet, score }`.
  - Snippets bounded to ~300–700 chars.

### 8. `brain_read`
- **Purpose:** Safe, bounded Markdown reader for a specific knowledge file.
- **Input:**
  - Exactly one of `forkos_id` (`str`, UUID) or `relative_path` (`str`).
  - `heading` (optional `str`): Extract only content under a specific heading.
- **Output:**
  - `title`: Extracted title.
  - `relative_path`: Relative Vault path.
  - `forkos_id`: UUID if managed.
  - `forkos_type`: Entity type if managed.
  - `frontmatter`: Safe whitelisted frontmatter subset.
  - `headings`: List of all top-level headings in the note.
  - `content`: Markdown text (bounded to ~12,000 chars default, max 40,000 chars).
  - `truncated`: Boolean.

---

## 6. Safety, Privacy & Immutability Guarantees

1. **Path Traversal & Symlink Safety:**
   - All paths resolved via `safe_vault_path()` ensuring targets reside strictly within `resolved_obsidian_vault_path`.
   - Symlinks resolving outside Vault root are rejected with `VAULT_PATH_ESCAPES`.
   - Hidden files/directories (`.*`) and system folders (`.git`, `.obsidian`, `.forkos-migration`) are blocked from reading and searching.
2. **Credential & Secret Scrubbing:**
   - No tool exposes environment variables, database URLs, API tokens, or user secrets.
   - Activity event payloads pass through a recursive scrubber that masks any key containing `token`, `secret`, `password`, `key`, `credential`.
3. **Database Immutability:**
   - H0 operations only execute SELECT queries.
   - Read-only test executes all 8 tools and verifies table fingerprints (`count(*)`, max IDs, md5 of core state) are byte-identical before and after.
4. **Vault Immutability:**
   - Knowledge tools open files strictly with `mode="r"`.
   - No mtime updates, no touching, no automatic frontmatter fixing.
   - Immutability test verifies Vault hashes and file mtimes are identical before and after tool calls.

---

## 7. Documentation & Setup Artifacts

Under `docs/hermes/`:
1. `README.md`: Explains the forkOS + f0rknbrain + Hermes mental model and boundaries.
2. `h0-brain-interface.md`: Technical documentation of the H0 Brain Interface architecture.
3. `h0-tool-contract.md`: Reference schema and example payloads for all 8 MCP tools.
4. `h0-setup.md`: Setup instructions and example config for connecting Hermes or any MCP client to `http://127.0.0.1:8787/mcp`.
5. `roadmap.md`: The H-series evolutionary roadmap (H0 through H6).
6. Main `README.md` updated with a brief pointer to `docs/hermes/`.

---

## 8. Verification Strategy

1. **Unit Tests:**
   - `test_agent_models.py`: Envelopes, bounds, and serializers.
   - `test_agent_knowledge.py`: Lexical search, ranking, heading extraction, unmanaged notes, path safety, snippet bounding.
   - `test_agent_context.py`: Briefing, operational search, project context, activity sanitization.
2. **MCP Contract & Integration Tests:**
   - `test_agent_mcp.py`: Server startup, `/mcp` HTTP endpoint mounting, tool listing, schemas, read-only annotations, error formatting.
   - Client smoke test using official `mcp.client.streamable_http.streamable_http_client` over ASGI transport.
3. **Immutability Verifications:**
   - DB state fingerprint comparison before & after all 8 tool invocations.
   - Vault file hashes and mtimes comparison before & after all tool invocations.
4. **Quality Gates:**
   - `pytest` across affected suites.
   - `ruff check backend/app/integrations/agent backend/tests`.
   - `git diff --check`.
