"""Yüksek güvenli kimlik ve sır koruma yardımcıları.

Bu modül H2 ve A3 için tek kanonik sır deseni kaynağıdır. İkinci bir regex
listesi ÜRETİLMEZ; kimlik bilgisi biçimleri merkezi olarak burada tanımlanır.

Bu bir genel PII/NLP sınıflandırıcısı DEĞİLDİR; yalnız apaçık kimlik bilgisi
ve token biçimlerini deterministik olarak yakalar.
"""

from __future__ import annotations

import re

#: Deterministik, YÜKSEK GÜVENLİ sır desenleri.
_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"-----\s*BEGIN[^-]*PRIVATE KEY-----", re.IGNORECASE),
    re.compile(r"\bBearer\s+[A-Za-z0-9\-._~+/]{20,}", re.IGNORECASE),
    re.compile(
        r"\b(?:password|passwd|pwd|api[_-]?key|secret[_-]?key|client[_-]?secret"
        r"|access[_-]?token|refresh[_-]?token)\b\s*[:=]\s*\S{6,}",
        re.IGNORECASE,
    ),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
)


def looks_like_secret(*parts: str | None) -> bool:
    """Verilen metin parçalarında apaçık kimlik bilgisi var mı (deterministik)."""
    blob = "\n".join(part for part in parts if part)
    return any(pattern.search(blob) for pattern in _SECRET_PATTERNS)


contains_high_confidence_secret = looks_like_secret

__all__ = [
    "_SECRET_PATTERNS",
    "contains_high_confidence_secret",
    "looks_like_secret",
]
