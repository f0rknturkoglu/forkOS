# forkOS × career-ops — C1: Integration Foundation, Version Pinning & Doctor Design

- **Date**: 2026-09-25
- **Status**: Approved
- **Scope**: Integration boundary, version pinning, runner, capability registry, workspace isolation, doctor diagnostics.

---

## 1. Context & Architectural Principles

### 1.1 Invariant Ownership
```text
Hermes (Orchestrator)
    ↓
forkOS (Canonical Engine)
    ├── canonical career state → PostgreSQL
    ├── durable knowledge      → Obsidian
    └── CareerOps integration
             ↓
        career-ops engine (Search / Analysis / Generation Engine ONLY)
```

- **Single Source of Truth**: forkOS PostgreSQL is the only canonical owner of durable career state (`Opportunity`, `Application`, `Interview`, `CareerStory`, `CareerConnection`).
- **No Second Source of Truth**: career-ops tracker files (`data/applications.md`, `data/pipeline.md`, SQLite-derived tracker state, reports used as tracker state) must **NEVER** become authoritative forkOS state.
- **Fail Closed**: Any failure in career-ops (missing, wrong commit, timeout, malformed output) must never break forkOS core boot, operations, or mutate canonical state.

---

## 2. Upstream Identity & Version Pinning

The integration baseline is strictly pinned:
- **Repository**: `career-ops-hq/career-ops`
- **Package Version**: `1.34.0`
- **Pinned Commit**: `6326eb5d3804e8cb20d28acd5701a4e603a301f9`

Defined as canonical constants in `backend/app/integrations/career_ops/config.py`:
```python
CAREER_OPS_UPSTREAM_REPO = "career-ops-hq/career-ops"
CAREER_OPS_PINNED_VERSION = "1.34.0"
CAREER_OPS_PINNED_COMMIT = "6326eb5d3804e8cb20d28acd5701a4e603a301f9"
```

Provisioning:
- `.vendor/career-ops` (gitignored in forkOS).
- `scripts/setup_career_ops.sh` clones `--depth 1` at the pinned commit and runs `npm install --ignore-scripts`.
- `Makefile` includes `career-ops-setup` target.

---

## 3. Configuration & Fail-Closed Settings

Added to `backend/app/config.py`:
```python
career_ops_enabled: bool = False
career_ops_root: str = ""  # Resolves to repo-root/.vendor/career-ops if empty
career_ops_node_bin: str = "node"
career_ops_timeout_seconds: float = 30.0
career_ops_max_buffer_bytes: int = 512 * 1024  # 512 KB stdout/stderr limit
career_ops_runtime_dir: str = ""  # Resolves to backend/data/runtime/career-ops if empty
```

- When `career_ops_enabled = False`: Zero runtime dependency. `doctor` reports `DISABLED`. All capabilities report `disabled`. forkOS runs normally.
- When `career_ops_enabled = True` but runtime/node/checkout missing: `doctor` reports `UNAVAILABLE`. Capabilities report `unavailable`. forkOS remains healthy.

---

## 4. Workspace Isolation & Anti-Corruption Boundary

To protect against upstream scripts auto-creating tracker files in the code checkout or personal paths:
- Runtime workspace managed at `backend/data/runtime/career-ops/`:
  - `generated-input/` (ephemeral input payloads passed to scripts)
  - `temporary-output/` (raw script outputs and reports before normalization)
  - `cache/` (scratch cache)
- All script invocations receive explicit environment variables:
  - `CAREER_OPS_ROOT=<runtime_workspace>`
  - `CAREER_OPS_DATA_DIR=<runtime_workspace>`
  - `CAREER_OPS_TRACKER=<runtime_workspace>/ephemeral-tracker.md`
- Subprocess invocations pass `--target <runtime_workspace>` when supported (e.g. `doctor.mjs`).

---

## 5. Safe Runner Boundary

Implemented in `backend/app/integrations/career_ops/runner.py`:
- Protocol `CareerOpsRunner` with `SubprocessCareerOpsRunner`.
- Allowlist of executable scripts (`doctor.mjs`, etc.). Reject any script not on the allowlist with `CareerOpsSecurityError`.
- No `shell=True`. Arguments passed as discrete tokens to `asyncio.create_subprocess_exec`.
- Strict timeouts (`career_ops_timeout_seconds`), raising `CareerOpsTimeoutError`.
- Output buffer bounds (`career_ops_max_buffer_bytes`), preventing memory exhaustion if a script dumps excessive output.
- Environment sanitization: Strips sensitive credentials, inherits only standard `PATH`, `HOME`, `TMPDIR`, and injects isolated `CAREER_OPS_*` variables.
- Typed errors:
  - `CareerOpsError` (base)
  - `CareerOpsConfigurationError`
  - `CareerOpsUnavailableError`
  - `CareerOpsVersionMismatchError`
  - `CareerOpsTimeoutError`
  - `CareerOpsExecutionError`
  - `CareerOpsInvalidOutputError`
  - `CareerOpsSecurityError`

---

## 6. Capability Registry

Implemented in `backend/app/integrations/career_ops/capabilities.py`:
- Typed capability models: `CareerOpsCapabilityId`, `CapabilityStatus` (`supported`, `unavailable`, `disabled`, `unknown`).
- Declarative registry covering all planned domains:
  - `discovery.scan`, `discovery.reverse_ats`, `discovery.liveness`
  - `job.extract`, `job.repost_analysis`, `job.legitimacy`
  - `evaluation.deep`, `evaluation.requirements`, `evaluation.compensation`, `evaluation.work_authorization`
  - `cv.tailor`, `cv.verify_facts`, `cv.render_pdf`, `cv.render_latex`, `cv.visual_validate`
  - `application.cover_letter`, `application.answers`, `application.prefill`
  - `interview.prepare`, `interview.practice`, `interview.debrief`
  - `analytics.funnel`, `analytics.rejection_patterns`, `analytics.skill_gap`, `analytics.calibration`
- In C1: Only doctor/foundation capabilities are active; all domain-specific capabilities are declared and queryable, returning `unavailable` or `disabled`.

---

## 7. Doctor & Diagnostics

Implemented in `backend/app/integrations/career_ops/doctor.py` and `adapter.py`:
- Status enum: `READY`, `DISABLED`, `UNAVAILABLE`, `VERSION_MISMATCH`, `MISCONFIGURED`, `DEGRADED`.
- Checks:
  1. Integration enabled check.
  2. Node runtime presence & version check (major >= 18, recommended >= 22.5).
  3. Career-ops checkout presence & directory integrity.
  4. Core files presence (`package.json`, `doctor.mjs`, `path-resolver.mjs`).
  5. Version check (`package.json` version == `1.34.0`).
  6. Git commit check (actual HEAD commit == `6326eb5d3804e8cb20d28acd5701a4e603a301f9`).
  7. Engine doctor probe: Execute `doctor.mjs --target <runtime_workspace> --json` via the runner in the isolated workspace.
  8. Capability inventory audit.
- Exposing surfaces:
  - CLI: `python -m app.cli career-doctor` (rich formatted table & checks)
  - CLI status: `python -m app.cli status` includes Career Engine line.
  - REST API: `GET /api/system/career-ops/doctor` (read-only diagnostic endpoint).

---

## 8. State Invariant & Security Proof

- **Zero Canonical Writes**: C1 codebase contains zero database write operations for `Opportunity`, `Application`, `Interview`, `CareerStory`, `CareerConnection`, `Document`, `Todo`, `Project`, `Learning`, or `Obsidian`.
- **Zero Hermes Product Tools**: No `forkos_career_*` MCP tools added. Existing 34 MCP tools retained.
- **Fail-Closed**: In all failure conditions, returns typed errors and never crashes the host API or mutates database state.

---

## 9. Upgrade Procedure

Documented in `docs/integrations/career-ops.md`:
1. Select new upstream commit & version.
2. Update `CAREER_OPS_PINNED_VERSION` and `CAREER_OPS_PINNED_COMMIT` in `backend/app/integrations/career_ops/config.py`.
3. Run `scripts/setup_career_ops.sh` to update `.vendor/career-ops`.
4. Run `backend/tests/test_career_ops.py` to verify version and runner contracts.
5. Audit capability differences and update capability registry.
6. Commit the pin bump.
