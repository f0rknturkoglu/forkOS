"""Cluster deduplication and merging.

Two clusters that represent the same real-world posting can form when:
  - A Layer A and Layer B source both discover the same job, but the titles
    differ enough to miss the fuzzy match (≥ 0.90 threshold).
  - A company renames a role slightly between syncs.
  - The same job is posted on two ATS platforms (rare but possible).

This module finds candidate pairs and provides safe merge logic. Merging is
deliberately manual by default — the user reviews candidates and confirms.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Any

from .identity import cities_compatible, title_similarity
from .models import Job, JobCluster, Status, USER_OWNED_STATUSES, dt_to_str, new_cluster_id, norm_text, utcnow


@dataclass(slots=True)
class MergeCandidate:
    """Two clusters that likely represent the same job."""

    cluster_a: str
    cluster_b: str
    title_a: str = ""
    title_b: str = ""
    company: str = ""
    similarity: float = 0.0
    reason: str = ""


def find_duplicates(conn: sqlite3.Connection, *, threshold: float = 0.85) -> list[MergeCandidate]:
    """Find clusters that likely represent the same real-world posting.

    Two clusters are duplicate candidates only when:
      - Same normalised company name.
      - Title similarity ≥ threshold.
      - Compatible locations: one is empty, or they share a city, or the
        cities are substrings of each other. Different known cities → not a
        duplicate (same role, different office).
    """
    rows = conn.execute(
        """
        SELECT c.cluster_id, j.title, j.company, j.company_norm, j.city, j.location
          FROM job_clusters c
          JOIN jobs j ON j.job_id = c.canonical_job_id
         WHERE c.status NOT IN ('closed')
         ORDER BY j.company_norm, j.title
        """
    ).fetchall()

    # Group by normalised company name.
    by_company: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        key = row["company_norm"] or norm_text(row["company"])
        by_company.setdefault(key, []).append(dict(row))

    candidates: list[MergeCandidate] = []

    for company_key, clusters in by_company.items():
        if len(clusters) < 2:
            continue

        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                title_a = norm_text(clusters[i]["title"])
                title_b = norm_text(clusters[j]["title"])
                sim = title_similarity(title_a, title_b)

                if sim < threshold:
                    continue

                # Check location compatibility.
                city_a = norm_text(clusters[i].get("city") or clusters[i].get("location"))
                city_b = norm_text(clusters[j].get("city") or clusters[j].get("location"))
                if not cities_compatible(city_a, city_b):
                    continue

                candidates.append(MergeCandidate(
                        cluster_a=clusters[i]["cluster_id"],
                        cluster_b=clusters[j]["cluster_id"],
                        title_a=clusters[i]["title"],
                        title_b=clusters[j]["title"],
                        company=clusters[i]["company"],
                        similarity=round(sim, 3),
                        reason=f"title similarity {sim:.0%}",
                    ))

    # Sort by similarity descending so the best matches are reviewed first.
    candidates.sort(key=lambda c: c.similarity, reverse=True)
    return candidates


def merge_clusters(
    conn: sqlite3.Connection,
    keep_id: str,
    discard_id: str,
) -> dict[str, Any]:
    """Merge discard_id into keep_id. Returns what changed.

    Rules:
      - All jobs from discard move to keep.
      - The best user status wins (user-owned > system-owned).
      - Notes from discard are appended to keep's notes.
      - `applied_at` keeps the earliest non-null value.
      - Canonical is re-elected from the merged set.
      - The discard cluster is NOT deleted (invariant: nothing is ever deleted).
        Its status is set to `closed` with a note explaining the merge.
    """
    result: dict[str, Any] = {
        "merged": False,
        "jobs_moved": 0,
        "status_change": None,
    }

    # Validate both clusters exist.
    keep = conn.execute(
        "SELECT * FROM job_clusters WHERE cluster_id = ?", (keep_id,)
    ).fetchone()
    discard = conn.execute(
        "SELECT * FROM job_clusters WHERE cluster_id = ?", (discard_id,)
    ).fetchone()

    if keep is None or discard is None:
        return result

    keep_status = Status(keep["status"])
    discard_status = Status(discard["status"])

    with conn:
        # Move all jobs from discard to keep.
        cur = conn.execute(
            "UPDATE jobs SET cluster_id = ? WHERE cluster_id = ?",
            (keep_id, discard_id),
        )
        result["jobs_moved"] = cur.rowcount

        if result["jobs_moved"] == 0:
            return result

        # Choose the best status: user-owned wins, otherwise keep's.
        final_status = keep_status
        if discard_status in USER_OWNED_STATUSES and keep_status not in USER_OWNED_STATUSES:
            final_status = discard_status
            result["status_change"] = f"{keep_status.value} → {discard_status.value}"

        # Merge notes.
        merged_notes = (keep["notes"] or "").strip()
        discard_notes = (discard["notes"] or "").strip()
        if discard_notes and discard_notes not in merged_notes:
            merged_notes = f"{merged_notes}\n[merged from {discard_id[:8]}]: {discard_notes}".strip()

        # Best applied_at: earliest non-null.
        applied_at = keep["applied_at"]
        if applied_at is None and discard["applied_at"] is not None:
            applied_at = discard["applied_at"]

        now = dt_to_str(utcnow())

        conn.execute(
            """
            UPDATE job_clusters
               SET status = ?,
                   notes = ?,
                   applied_at = ?,
                   status_changed_at = ?
             WHERE cluster_id = ?
            """,
            (final_status.value, merged_notes, applied_at, now, keep_id),
        )

        # Mark discard as closed with merge note.
        conn.execute(
            """
            UPDATE job_clusters
               SET status = ?,
                   notes = ?,
                   status_changed_at = ?
             WHERE cluster_id = ?
            """,
            (
                Status.CLOSED.value,
                f"merged into {keep_id} on {now}",
                now,
                discard_id,
            ),
        )

    # Re-elect canonical from the merged cluster.
    canonical = conn.execute(
        """
        SELECT job_id FROM jobs
         WHERE cluster_id = ?
         ORDER BY (layer = 'A') DESC,
                  is_open DESC,
                  CASE date_source WHEN 'employer' THEN 0 WHEN 'updated' THEN 1 ELSE 2 END ASC,
                  last_seen DESC
         LIMIT 1
        """,
        (keep_id,),
    ).fetchone()

    with conn:
        conn.execute(
            "UPDATE job_clusters SET canonical_job_id = ? WHERE cluster_id = ?",
            (canonical["job_id"] if canonical else None, keep_id),
        )

    result["merged"] = True
    result["canonical"] = canonical["job_id"] if canonical else None
    return result
