"""Identity resolution: which row is this, and which cluster does it belong to.

Resolution order (docs/SCHEMA.md §3):

    1. (source, external_id)  -> same row, refresh its url
    2. job_id (canonical URL hash) -> same row
    3. cluster match on (company, title, city) -> new row, existing cluster
    4. nothing matched -> new row, new cluster

Read-only: this module decides, `db.py` writes.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from difflib import SequenceMatcher
from enum import Enum

from .models import Job, norm_text

#: Title similarity required to fold two records into one cluster. Raised from
#: a first guess of 0.80 — "Junior Backend Engineer" vs "Junior Frontend
#: Engineer" scores 0.84, and those are not the same job.
DEFAULT_TITLE_THRESHOLD = 0.90


class MatchKind(str, Enum):
    EXTERNAL_ID = "external_id"
    JOB_ID = "job_id"
    CLUSTER_EXACT = "cluster_exact"
    CLUSTER_FUZZY = "cluster_fuzzy"
    NEW = "new"


@dataclass(slots=True)
class Resolution:
    """What `db.upsert_job` should do with an incoming record."""

    job_id: str
    cluster_id: str | None
    matched_by: MatchKind
    #: No existing jobs row — insert one.
    is_new_job: bool
    #: No existing cluster — create one.
    is_new_cluster: bool
    #: Set when rule 1 fired and the source moved the posting's URL.
    previous_url: str | None = None

    @property
    def url_moved(self) -> bool:
        return self.previous_url is not None


def resolve(
    conn: sqlite3.Connection,
    job: Job,
    *,
    title_threshold: float = DEFAULT_TITLE_THRESHOLD,
) -> Resolution:
    """Decide the identity of an incoming record. Does not write."""

    # -- 1. the source's own id wins, because URLs move and ids do not -------
    if job.external_id:
        row = conn.execute(
            "SELECT job_id, cluster_id, url FROM jobs WHERE source = ? AND external_id = ?",
            (job.source, job.external_id),
        ).fetchone()
        if row is not None:
            moved = row["url"] if row["url"] != job.url else None
            return Resolution(
                job_id=row["job_id"],
                cluster_id=row["cluster_id"],
                matched_by=MatchKind.EXTERNAL_ID,
                is_new_job=False,
                is_new_cluster=False,
                previous_url=moved,
            )

    # -- 2. fall back to the URL hash ---------------------------------------
    row = conn.execute(
        "SELECT job_id, cluster_id FROM jobs WHERE job_id = ?", (job.job_id,)
    ).fetchone()
    if row is not None:
        return Resolution(
            job_id=row["job_id"],
            cluster_id=row["cluster_id"],
            matched_by=MatchKind.JOB_ID,
            is_new_job=False,
            is_new_cluster=False,
        )

    # -- 3. a different source may already carry this posting ---------------
    match = find_cluster(conn, job, title_threshold=title_threshold)
    if match is not None:
        cluster_id, kind = match
        return Resolution(
            job_id=job.job_id,
            cluster_id=cluster_id,
            matched_by=kind,
            is_new_job=True,
            is_new_cluster=False,
        )

    # -- 4. genuinely new ---------------------------------------------------
    return Resolution(
        job_id=job.job_id,
        cluster_id=None,
        matched_by=MatchKind.NEW,
        is_new_job=True,
        is_new_cluster=True,
    )


def find_cluster(
    conn: sqlite3.Connection,
    job: Job,
    *,
    title_threshold: float = DEFAULT_TITLE_THRESHOLD,
) -> tuple[str, MatchKind] | None:
    """Find an existing cluster for a posting seen under a different URL."""

    exact = conn.execute(
        """
        SELECT cluster_id FROM jobs
         WHERE cluster_key = ? AND cluster_key != ''
           AND NOT (source = ? AND is_open = 1)
         LIMIT 1
        """,
        (job.cluster_key, job.source),
    ).fetchone()
    if exact is not None:
        return exact["cluster_id"], MatchKind.CLUSTER_EXACT

    # Candidates share a company. Two live postings from the *same* source are
    # never folded together: if a source returns both in one sync, they really
    # are two openings. Closed rows from that source stay eligible, which is
    # how a URL change with no external_id still finds its way home.
    candidates = conn.execute(
        """
        SELECT cluster_id, title, city, location FROM jobs
         WHERE company_norm = ?
           AND NOT (source = ? AND is_open = 1)
        """,
        (job.company_norm, job.source),
    ).fetchall()
    if not candidates:
        return None

    incoming_title = norm_text(job.title)
    incoming_city = norm_text(job.city or job.location)

    best: tuple[float, str] | None = None
    for row in candidates:
        if not cities_compatible(incoming_city, norm_text(row["city"] or row["location"])):
            continue
        similarity = title_similarity(incoming_title, norm_text(row["title"]))
        if similarity >= title_threshold and (best is None or similarity > best[0]):
            best = (similarity, row["cluster_id"])

    return (best[1], MatchKind.CLUSTER_FUZZY) if best else None


def title_similarity(left: str, right: str) -> float:
    """Max of sequence ratio and token overlap.

    Token overlap catches reorderings a plain sequence ratio misses, e.g.
    "Backend Engineer (Junior)" against "Junior Backend Engineer".
    """
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0

    sequence = SequenceMatcher(None, left, right).ratio()

    left_tokens, right_tokens = set(left.split()), set(right.split())
    union = left_tokens | right_tokens
    jaccard = len(left_tokens & right_tokens) / len(union) if union else 0.0

    return max(sequence, jaccard)


def cities_compatible(left: str, right: str) -> bool:
    """Unknown on either side is tolerated; two known, different cities are not.

    Same company, same title, Madrid vs Barcelona is two openings, not one.
    """
    if not left or not right:
        return True
    return left == right or left in right or right in left
