# Contributing to forkOS

Thank you for your interest in contributing to **forkOS**!

forkOS is an open-source, local-first personal operating system designed for single-user productivity, privacy, and connected knowledge. We welcome improvements, bug fixes, and suggestions that align with our core local-first philosophy.

---

## 1. Core Architectural Principles

Before contributing code, please review the contract rules in [AGENTS.md](AGENTS.md) and [docs/mimari.md](docs/mimari.md):

1. **Local-Only & Loopback Default:** Services bind strictly to `127.0.0.1`. No remote authentication or multi-tenant abstraction layers exist or should be added.
2. **Zero External Telemetry:** User data, notes, and metrics must never leave the machine. No third-party tracking, analytics, or external AI API calls unless explicitly configured locally.
3. **Entity Backbone:** Every searchable or linkable entity table must use a primary key that foreign-keys to `entity.id`. Entities are created via `backend/app/core/entity.py` helpers.
4. **Append-Only Events:** The `event` table is append-only. Call `log_event()` after meaningful mutations.
5. **Registry Pattern:** Backend modules are registered in `backend/app/modules/__init__.py::MODULES`; frontend modules in `frontend/src/modules/index.ts`. No manual route imports in `main.py`.
6. **AsyncPG Migrations:** Each Alembic migration step must use a single SQL statement per `op.execute()` call (asyncpg does not allow multiple DDLs in a single prepared statement).
7. **Design System:** Use design tokens and `@/core/ui` primitives. Avoid raw `<input>` or hardcoded hex colors.

---

## 2. Local Development Workflow

### Prerequisites
- Docker or OrbStack (or Podman)
- Python 3.12+ (for local scripts/tests)
- Node.js 22+ (for frontend)

### Quick Start
```bash
# 1. Clone repository
git clone https://github.com/f0rknturkoglu/forkOS.git
cd forkOS

# 2. Automated bootstrap & environment setup
python3 scripts/setup_all.py
# or
make setup

# 3. Start development stack
make up-dev CO="docker compose"
```

Services will be available at:
- Web Application: [http://127.0.0.1:5173](http://127.0.0.1:5173) (Dev) or [http://127.0.0.1:8788](http://127.0.0.1:8788) (Stable)
- FastAPI / Swagger Docs: [http://127.0.0.1:8787/docs](http://127.0.0.1:8787/docs)

---

## 3. Running Verification & Tests

Always run the test and verification suite before submitting a Pull Request:

```bash
# Run backend contract and isolation tests
make test CO="docker compose"

# Run full project verification (Linter, TypeCheck, API contract sync, dead export checks)
make verify CO="docker compose"

# Verify system health
python3 scripts/forkos.py doctor
```

---

## 4. Submitting Changes

1. **Fork the repository** on GitHub.
2. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/my-improvement
   ```
3. **Commit your changes**:
   - Write clear, concise commit messages following conventional commits (`feat:`, `fix:`, `docs:`, `refactor:`).
   - Ensure `git diff --check` passes without whitespace issues.
4. **Push to your fork** and open a **Pull Request** against `main`.
5. Clearly describe the problem, the solution, and any manual or automated tests performed.

---

## 5. Code of Conduct

All contributors are expected to uphold our [Code of Conduct](CODE_OF_CONDUCT.md). Please treat everyone with respect and kindness.
