"""Literal user dates and capacity: assistant statements cannot establish facts."""

import calendar
import re
from contextlib import suppress
from datetime import date, datetime, timedelta
from decimal import Decimal

from app.core.time import local_today
from app.modules.goal.studio_authoring import user_deadline


def deadline(data):
    """Explicit user-relative dates, anchored to their message, not retry time."""
    words = {
        "bir": 1,
        "iki": 2,
        "üç": 3,
        "dört": 4,
        "beş": 5,
        "altı": 6,
        "yedi": 7,
        "sekiz": 8,
        "dokuz": 9,
        "on": 10,
    }
    for turn in sorted(data.get("turns", {}).values(), key=lambda t: t["at"], reverse=True):
        text = turn["message"].casefold().replace("i\u0307", "i")
        today = local_today(datetime.fromisoformat(turn["at"]))
        if re.search(r"\byarın\b", text):
            return today + timedelta(days=1)
        match = re.search(
            r"\b(\d{1,3}|" + "|".join(words) + r")\s+(gün|hafta|ay|yıl)\s+(?:içinde|sonra|kaldı)\b",
            text,
        )
        if not match:
            match = re.search(
                r"\b(?:önümüzdeki|gelecek)\s+(\d{1,3}|"
                + "|".join(words)
                + r")\s+(gün|hafta|ay|yıl)(?:da|de)?\b",
                text,
            )
        if match:
            n = words.get(match[1]) or int(match[1])
            if not 0 < n <= 120:
                continue
            if match[2] in {"gün", "hafta"}:
                return today + timedelta(days=n * (7 if match[2] == "hafta" else 1))
            months = n * (12 if match[2] == "yıl" else 1)
            year, month = divmod(today.year * 12 + today.month - 1 + months, 12)
            return date(year, month + 1, min(today.day, calendar.monthrange(year, month + 1)[1]))
    return user_deadline(data)


def numeric_target(data):
    messages = [m["text"] for m in data.get("messages", []) if m.get("role") == "user"]
    if not messages:
        return None
    text = messages[-1].casefold()
    explicit = re.search(
        r"(?:en az|hedef(?:im)?\s*[:=]?)\s*(\d+(?:[.,]\d+)?)\s*(?:\+|puan|points?\b|score\b)", text
    )
    if explicit:
        return Decimal(explicit[1].replace(",", "."))
    match = re.search(
        r"(?:en az\s+|hedef(?:im)?\s*[:=]?\s*)?(\d+(?:[.,]\d+)?)\s*(?:\+|puan|points?\b|score\b)",
        text,
    )
    return Decimal(match[1].replace(",", ".")) if match else None


def requested_learning(data):
    """Only explicit user intent, never an inferred goal-category requirement."""
    messages = [m["text"] for m in data.get("messages", []) if m.get("role") == "user"]
    if not messages:
        return False
    text = messages[-1].casefold()
    if re.search(
        r"öğrenme.{0,60}(?:gerekmiyor|gerekli değil|istemiyorum|olmasın|ekleme)|no learning", text
    ):
        return False
    return bool(
        re.search(r"öğrenme.{0,80}(?:konu|plan|çalışma|ekle|istiyor)|learning topics", text)
    )


def dates(data):
    allowed = set()
    relative = deadline(data)
    if relative:
        allowed.add(relative)
    months = {
        "ocak": 1,
        "şubat": 2,
        "mart": 3,
        "nisan": 4,
        "mayıs": 5,
        "haziran": 6,
        "temmuz": 7,
        "ağustos": 8,
        "eylül": 9,
        "ekim": 10,
        "kasım": 11,
        "aralık": 12,
    }
    numbers = {
        "bir": 1,
        "iki": 2,
        "üç": 3,
        "dört": 4,
        "beş": 5,
        "altı": 6,
        "yedi": 7,
        "sekiz": 8,
        "dokuz": 9,
        "on": 10,
    }
    for turn in data.get("turns", {}).values():
        text = turn["message"].casefold()
        for raw in re.findall(r"\b\d{4}-\d{2}-\d{2}\b", text):
            with suppress(ValueError):
                allowed.add(date.fromisoformat(raw))
        for d, m, y in re.findall(r"\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b", text):
            with suppress(ValueError):
                allowed.add(date(int(y), int(m), int(d)))
        for d, m, y in re.findall(r"\b(\d{1,2})\s+(" + "|".join(months) + r")\s+(\d{4})\b", text):
            with suppress(ValueError):
                allowed.add(date(int(y), months[m], int(d)))
        year = re.search(
            r"(?:önümüzdeki|gelecek)\s+(\d{1,2}|bir|iki|üç|dört|beş|altı|yedi|sekiz|dokuz|on)\s*yıl",
            text,
        )
        if year:
            count = numbers.get(year[1]) or int(year[1])
            if 0 < count <= 20:
                today = local_today(datetime.fromisoformat(turn["at"]))
                end_year = today.year + count
                allowed.add(
                    date(
                        end_year,
                        today.month,
                        min(today.day, calendar.monthrange(end_year, today.month)[1]),
                    )
                )
    return allowed


def availability(data):
    """Only explicit, unambiguous user availability; unknown clock time stays unset."""
    messages = [
        m["text"].casefold().replace("i\u0307", "i")
        for m in data.get("messages", [])
        if m.get("role") == "user"
    ]
    if not messages:
        return {}
    text = messages[-1]
    result = {}
    if re.search(r"hafta son(?:u|ları).*?(?:çalışam|uygun değil|müsait değil|hariç)", text):
        result["weekdays"] = list(range(5))
    elif re.search(r"(?:sadece|yalnız(?:ca)?)\s+hafta son", text):
        result["weekdays"] = [5, 6]
    elif re.search(r"(?:sadece|yalnız(?:ca)?)\s+hafta iç", text):
        result["weekdays"] = list(range(5))
    names = {
        "pazartesi": 0,
        "salı": 1,
        "çarşamba": 2,
        "perşembe": 3,
        "cuma": 4,
        "cumartesi": 5,
        "pazar": 6,
    }
    selected = [i for day, i in names.items() if re.search(r"\b" + day + r"\b", text)]
    if (
        selected
        and re.search(r"sadece|yalnızca", text)
        and re.search(r"çalışabil|müsait|uygun", text)
    ):
        result["weekdays"] = selected
    match = re.search(r"\b(\d{1,2}):(\d{2})\s*(?:-|–|ile)\s*(\d{1,2}):(\d{2})\b", text)
    if (
        match
        and re.search(r"çalışabil|müsait|uygun", text)
        and not re.search(r"çalışam|uygun değil|müsait değil", text)
    ):
        h1, m1, h2, m2 = map(int, match.groups())
        start, end = h1 * 60 + m1, h2 * 60 + m2
        if h1 < 24 and h2 <= 24 and m1 < 60 and m2 < 60 and 0 <= start < end <= 1440:
            result.update(available_start_min=start, available_end_min=end)
    return result


def requested_tasks(data):
    messages = [
        m["text"].casefold().replace("i\u0307", "i")
        for m in data.get("messages", [])
        if m.get("role") == "user"
    ]
    if not messages or not re.search(r"ekle|oluştur", messages[-1]):
        return None
    words = {
        "bir": 1,
        "iki": 2,
        "üç": 3,
        "dört": 4,
        "beş": 5,
        "altı": 6,
        "yedi": 7,
        "sekiz": 8,
        "dokuz": 9,
        "on": 10,
    }
    match = re.search(
        r"\b(\d{1,2}|" + "|".join(words) + r")\s+(?:(?:yeni|pratik|çalışma)\s+){0,2}görev\b",
        messages[-1],
    )
    if match:
        count = words.get(match[1]) or int(match[1])
        return count if 0 < count <= 20 else None
    return None
