"""Medya girdi dogrulama yardimcilari."""

from __future__ import annotations


def _known(value: str | None, values: list[str], label: str) -> str | None:
    if value is not None and value not in values:
        raise ValueError(f"{label} su olmali: {values}")
    return value


def nonnegative(value: float | None) -> float | None:
    if value is not None and value < 0:
        raise ValueError("progress/total negatif olamaz")
    return value


def score_range(value: int | None) -> int | None:
    if value is not None and not 0 <= value <= 10:
        raise ValueError("score 0-10 olmali")
    return value
