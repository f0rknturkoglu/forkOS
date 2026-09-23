"""A4: Semantic candidate politikaları ve kuralları.

Deterministik kurallar:
- Gizlilik vetosu (opt-out kalıpları -> candidate oluşturulmaz)
- Kararlı candidate_key ve revision türetimi
- Varış yeri (destination) yönlendirmesi
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
import uuid
from datetime import datetime

#: Gizlilik opt-out kalıpları (Türkçe ve İngilizce)
_PRIVACY_BLOCKED_PATTERNS = [
    re.compile(r"\b(bunu\s+)?haf[ıi]zaya\s+alma\b", re.IGNORECASE),
    re.compile(r"\b(bunu|bu\s+tercihimi)\s+hat[ıi]rlama\b", re.IGNORECASE),
    re.compile(
        r"\b(bunu|bu\s+bilgiyi)\s+(haf[ıi]zaya|memory.?e|belle[ğg]e)\s+kaydetme\b", re.IGNORECASE
    ),
    re.compile(r"\bbu\s+tercihimi\s+unut\b", re.IGNORECASE),
    re.compile(r"\b(do\s+not|don't)\s+remember(\s+this)?\b", re.IGNORECASE),
    re.compile(
        r"\b(do\s+not|don't)\s+(store|save)\s+(this|it)\s+(as|in|to)\s+(a\s+)?memor(?:y|ies)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(do\s+not|don't)\s+(store|save)\s+this\s+conversation\b", re.IGNORECASE),
    re.compile(r"\bforget\s+this\s+(preference|memory|fact)\b", re.IGNORECASE),
]


def is_privacy_blocked(text: str) -> bool:
    """Metinde açıkça hafızaya almama/unutturma talebi olup olmadığını kontrol eder."""
    normalized = unicodedata.normalize("NFKC", text or "")
    return any(pattern.search(normalized) for pattern in _PRIVACY_BLOCKED_PATTERNS)


def normalize_statement(text: str) -> str:
    """İfadeyi kimlikleme için normalize eder (küçük harf, tek boşluk)."""
    norm = unicodedata.normalize("NFKC", text or "").strip().casefold().replace("\u0307", "")
    return re.sub(r"\s+", " ", norm)


def compute_candidate_key(
    kind: str,
    scope: str,
    scope_project: str | None,
    subject_key: str | None,
    statement: str,
) -> str:
    """Tekrarları yakalayan kararlı candidate_key üretir."""
    norm_stmt = normalize_statement(statement)
    payload = f"v2:{kind}:{scope}:{scope_project or ''}:{subject_key or ''}:{norm_stmt}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compute_candidate_revision(
    candidate_id: str | uuid.UUID,
    candidate_key: str,
    status: str,
    recurrence_count: int,
    last_seen_at: datetime,
) -> str:
    """Optimistik eşzamanlılık için revizyon hash'i üretir."""
    iso_time = last_seen_at.isoformat() if hasattr(last_seen_at, "isoformat") else str(last_seen_at)
    payload = f"{candidate_id}:{candidate_key}:{status}:{recurrence_count}:{iso_time}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def resolve_destination(kind: str, scope: str, scope_project: str | None) -> str:
    """Aday türü ve kapsamına göre kanonik varış yeri önerir."""
    if kind == "commitment":
        return "operational"
    if kind in ("goal", "constraint", "decision") and scope == "session":
        return "hot_memory"
    if kind in ("identity", "preference", "correction"):
        return "durable_vault"
    if kind in ("project_knowledge", "lesson", "reference", "constraint", "decision", "goal"):
        return "durable_vault"
    return "durable_vault"
