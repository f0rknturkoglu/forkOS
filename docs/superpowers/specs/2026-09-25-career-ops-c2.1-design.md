# Design Specification: forkOS × career-ops — C2.1 Correctness & Canonical Merge Closure

## 1. Context and Motivation
A post-C2 audit identified 12 correctness and hardening gaps across the career-ops integration and opportunity ingestion pipeline:
1. `location_filter` in `portals.yml` projection used made-up `positive`/`negative` keys instead of upstream `always_allow`, `allow`, `block`, `block_hard`, `strict`.
2. Discovery bypassed pinned identity checks before spawning subprocesses.
3. Cross-URL discovery for the same job produced duplicate Opportunities because career-ops offers lacked `cluster_key`.
4. Ingestion refresh erased rich forkjob metadata (description, remote, compensation, score, skill_match_ratio) with sparse career-ops data.
5. Doctor reported hardcoded `capabilities_available = 1` and didn't honor `CAREER_OPS_DISCOVERY_ENABLED=false`.
6. `capHit` was recorded but didn't set `is_partial = True`.
7. Non-HTTP(S) URLs were not rejected at the adapter boundary.
8. Subprocess runner did not reap child processes on `asyncio.CancelledError`.
9. The JSON parser accepted stdout with prepended/appended non-JSON text.
10. The DB zero-mutation test didn't reach the READY probe path.
11. Career-ops sources were missing from the worker's `_source_catalog()` for lease calculation.
12. Documentation of `upstream.lock.json` drifted from reality.

## 2. Invariants
- **Single Canonical Database**: All state remains in forkOS PostgreSQL.
- **Zero LLM Tokens**: Pure deterministic parsing and filtering.
- **Non-Destructive Aggregation**: Incoming unknown/None facts never erase existing known facts on an `Opportunity`.
- **Deterministic Clustering**: Real jobs with the same company + title + location merge to one `Opportunity` regardless of differing URLs.
- **Fail Closed**: Any identity mismatch or disabled flag halts discovery before executing Node scripts.
