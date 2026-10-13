"""Literal user dates and capacity: assistant statements cannot establish facts."""

import calendar
import re
from contextlib import suppress
from datetime import date, datetime

from app.core.time import local_today
from app.modules.goal.studio_authoring import user_deadline


def dates(data):
    allowed = set()
    relative = user_deadline(data)
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
