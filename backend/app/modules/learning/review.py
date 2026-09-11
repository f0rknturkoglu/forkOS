"""Konu tekrari (SRS). Merkezi, deterministik ve saf: DB'siz test edilir.

Kural: her tekrar araligi buyutur/kuculttur; `forgot` konuyu AYNI GUNE geri
koyar (aralik 0). Kolaylik derecesi (ease) yalnizca asiri kolay/zor
derecelerde kayar; `medium` notr referanstir.
"""

from __future__ import annotations

#: Kullanicinin verdigi dereceler -- UI bu sirayla gosterir.
GRADES = ["forgot", "hard", "medium", "easy", "very_easy"]
LABELS = {
    "forgot": "Hatırlamadım",
    "hard": "Zor",
    "medium": "Orta",
    "easy": "Kolay",
    "very_easy": "Çok kolay",
}

EASE_MIN = 1.3
EASE_MAX = 3.0
MAX_INTERVAL = 365


def _clamp_ease(value: float) -> float:
    return round(min(EASE_MAX, max(EASE_MIN, value)), 2)


def next_review(interval_days: int, ease: float, grade: str) -> tuple[int, float]:
    """Bir sonraki araligi (gun) ve ease'i dondurur.

    `forgot` -> 0 gun (ayni gun tekrar) ve ease -0.20
    `hard`   -> max(1, round(i*1.2)), ease -0.15
    `medium` -> max(1, round(i*2.0)), ease degismez
    `easy`   -> max(1, round(i*2.5)), ease +0.15
    `very_easy` -> max(1, round(i*3.0)), ease +0.30
    """
    if grade not in GRADES:
        raise ValueError(f"gecersiz derece: {grade} (beklenen: {GRADES})")
    current = max(0, int(interval_days))
    if grade == "forgot":
        return 0, _clamp_ease(ease - 0.20)
    if grade == "hard":
        return min(MAX_INTERVAL, max(1, round(current * 1.2))), _clamp_ease(ease - 0.15)
    if grade == "medium":
        return min(MAX_INTERVAL, max(1, round(current * 2.0))), _clamp_ease(ease)
    if grade == "easy":
        return min(MAX_INTERVAL, max(1, round(current * 2.5))), _clamp_ease(ease + 0.15)
    return min(MAX_INTERVAL, max(1, round(current * 3.0))), _clamp_ease(ease + 0.30)
