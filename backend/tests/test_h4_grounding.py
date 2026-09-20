"""H4.1 kaynak temellendirmesi — düşmanca (adversarial) doğrulama testleri.

Değişmez: model, GERÇEK bir kaynak alıntısı ekleyerek uydurma normalize alanları
meşrulaştıramaz. Zincir şudur:

```text
source_excerpt  →  date_text / ham alan  →  normalize değer
```
Her adım deterministik kodla doğrulanır.
"""

from __future__ import annotations

import json

from app.integrations.local_cognition import contracts as contract_svc

CALENDAR_TEXT = "2026-2027 Güz Dönemi\nKayıt yenileme: 1 - 5 Eylül 2026\nDerslerin başlangıcı: 21 Eylül 2026\n"
HOLIDAY_TEXT = "Yarıyıl tatili: 25 Ocak - 5 Şubat 2027\n"
EN_TEXT = "Final exams: January 12-20, 2027\n"
DEADLINE_TEXT = "Application deadline: 30 September 2026\nSubmission deadline: 12 October 2026 23:00\n"
SCHEDULE_TEXT = "Pazartesi 09:00-11:00 Veri Yapıları\nÇarşamba 14:00-16:00 İngilizce\n"


def _calendar(item: dict, text: str = CALENDAR_TEXT):
    return contract_svc.validate_academic_calendar({"events": [item]}, text)


def _deadline(item: dict, text: str = DEADLINE_TEXT):
    return contract_svc.validate_deadlines({"deadlines": [item]}, text)


def _schedule(item: dict, text: str = SCHEDULE_TEXT):
    return contract_svc.validate_weekly_schedule({"blocks": [item]}, text)


# ---------------------------------------------------------------------------
# Akademik takvim (§25-§29/§93-§96)
# ---------------------------------------------------------------------------


def test_calendar_date_text_must_come_from_source_excerpt() -> None:
    """§94: alıntı gerçek ama `date_text` uydurma → REDDET."""
    outcome = _calendar(
        {
            "title": "Kayıt yenileme",
            "category": "registration",
            "date_text": "1 Ocak 2030",
            "start_date": None,
            "end_date": None,
            "source_excerpt": "Kayıt yenileme: 1 - 5 Eylül 2026",
        }
    )
    assert outcome.ok is False
    assert outcome.code == "SOURCE_FIELD_NOT_SUPPORTED"


def test_calendar_rejects_hallucinated_normalized_date() -> None:
    """§93: `date_text` doğru, normalize tarih uydurma → REDDET."""
    outcome = _calendar(
        {
            "title": "Kayıt yenileme",
            "category": "registration",
            "date_text": "1 - 5 Eylül 2026",
            "start_date": "2030-01-01",
            "end_date": "2030-01-05",
            "source_excerpt": "Kayıt yenileme: 1 - 5 Eylül 2026",
        }
    )
    assert outcome.ok is False
    assert outcome.code == "INVALID_DATE"


def test_calendar_accepts_conservative_null_normalized_dates() -> None:
    """§95/§12: eksik normalizasyon geçerlidir; uydurmadan iyidir."""
    outcome = _calendar(
        {
            "title": "Kayıt yenileme",
            "category": "registration",
            "date_text": "1 - 5 Eylül 2026",
            "start_date": None,
            "end_date": None,
            "source_excerpt": "Kayıt yenileme: 1 - 5 Eylül 2026",
        }
    )
    assert outcome.ok is True


def test_calendar_validates_turkish_shared_month_range() -> None:
    outcome = _calendar(
        {
            "title": "Kayıt yenileme",
            "category": "registration",
            "date_text": "1 - 5 Eylül 2026",
            "start_date": "2026-09-01",
            "end_date": "2026-09-05",
            "source_excerpt": "Kayıt yenileme: 1 - 5 Eylül 2026",
        }
    )
    assert outcome.ok is True
    assert outcome.payload["events"][0]["start_date"] == "2026-09-01"


def test_calendar_validates_cross_month_range() -> None:
    """§96: ay geçen aralık doğru normalize edilir."""
    outcome = _calendar(
        {
            "title": "Yarıyıl tatili",
            "category": "holiday",
            "date_text": "25 Ocak - 5 Şubat 2027",
            "start_date": "2027-01-25",
            "end_date": "2027-02-05",
            "source_excerpt": "Yarıyıl tatili: 25 Ocak - 5 Şubat 2027",
        },
        HOLIDAY_TEXT,
    )
    assert outcome.ok is True


def test_calendar_validates_english_date_range() -> None:
    """§29: İngilizce aralık da deterministik çözülür; yanlışı reddedilir."""
    good = _calendar(
        {
            "title": "Final exams",
            "category": "exam",
            "date_text": "January 12-20, 2027",
            "start_date": "2027-01-12",
            "end_date": "2027-01-20",
            "source_excerpt": "Final exams: January 12-20, 2027",
        },
        EN_TEXT,
    )
    assert good.ok is True

    wrong = _calendar(
        {
            "title": "Final exams",
            "category": "exam",
            "date_text": "January 12-20, 2027",
            "start_date": "2027-01-13",
            "end_date": "2027-01-20",
            "source_excerpt": "Final exams: January 12-20, 2027",
        },
        EN_TEXT,
    )
    assert wrong.ok is False
    assert wrong.code == "INVALID_DATE"


def test_calendar_rejects_normalized_date_when_source_has_no_year() -> None:
    """§68: yıl yoksa normalize tarih UYDURULAMAZ."""
    text = "Final sınavı: 20 Kasım\n"
    outcome = _calendar(
        {
            "title": "Final sınavı",
            "category": "exam",
            "date_text": "20 Kasım",
            "start_date": "2026-11-20",
            "end_date": None,
            "source_excerpt": "Final sınavı: 20 Kasım",
        },
        text,
    )
    assert outcome.ok is False
    assert outcome.code == "INVALID_DATE"

    conservative = _calendar(
        {
            "title": "Final sınavı",
            "category": "exam",
            "date_text": "20 Kasım",
            "start_date": None,
            "end_date": None,
            "source_excerpt": "Final sınavı: 20 Kasım",
        },
        text,
    )
    assert conservative.ok is True


def test_calendar_rejects_reversed_range() -> None:
    outcome = _calendar(
        {
            "title": "Kayıt yenileme",
            "category": "registration",
            "date_text": "1 - 5 Eylül 2026",
            "start_date": "2026-09-05",
            "end_date": "2026-09-01",
            "source_excerpt": "Kayıt yenileme: 1 - 5 Eylül 2026",
        }
    )
    assert outcome.ok is False
    assert outcome.code == "INVALID_DATE"


def test_calendar_still_rejects_excerpt_outside_input() -> None:
    """§6: mevcut katı alıntı kapısı korunur."""
    outcome = _calendar(
        {
            "title": "Uydurma",
            "category": "exam",
            "date_text": "1 Eylül 2026",
            "start_date": None,
            "end_date": None,
            "source_excerpt": "Bu metin kaynakta yok",
        }
    )
    assert outcome.ok is False
    assert outcome.code == "SOURCE_EXCERPT_NOT_FOUND"


# ---------------------------------------------------------------------------
# Deadline (§30/§31)
# ---------------------------------------------------------------------------


def test_deadline_rejects_hallucinated_due_date() -> None:
    """§30: yıl kaydırılmış normalize tarih reddedilir."""
    outcome = _deadline(
        {
            "title": "Application deadline",
            "kind": "application",
            "date_text": "30 September 2026",
            "due_date": "2027-09-30",
            "due_time": None,
            "source_excerpt": "Application deadline: 30 September 2026",
        }
    )
    assert outcome.ok is False
    assert outcome.code == "INVALID_DATE"


def test_deadline_rejects_unsourced_due_time() -> None:
    """§31: kaynakta saat yoksa `due_time` uydurulamaz."""
    outcome = _deadline(
        {
            "title": "Submission deadline",
            "kind": "submission",
            "date_text": "12 October 2026",
            "due_date": None,
            "due_time": "23:59",
            "source_excerpt": "Submission deadline: 12 October 2026",
        }
    )
    assert outcome.ok is False
    assert outcome.code == "INVALID_TIME"


def test_deadline_accepts_sourced_due_date_and_time() -> None:
    outcome = _deadline(
        {
            "title": "Submission deadline",
            "kind": "submission",
            "date_text": "12 October 2026 23:00",
            "due_date": "2026-10-12",
            "due_time": "23:00",
            "source_excerpt": "Submission deadline: 12 October 2026 23:00",
        }
    )
    assert outcome.ok is True


def test_deadline_accepts_conservative_nulls() -> None:
    outcome = _deadline(
        {
            "title": "Application deadline",
            "kind": "application",
            "date_text": "30 September 2026",
            "due_date": None,
            "due_time": None,
            "source_excerpt": "Application deadline: 30 September 2026",
        }
    )
    assert outcome.ok is True


def test_deadline_rejects_unsourced_date_text() -> None:
    outcome = _deadline(
        {
            "title": "Application deadline",
            "kind": "application",
            "date_text": "30 Eylül 2027",
            "due_date": None,
            "due_time": None,
            "source_excerpt": "Application deadline: 30 September 2026",
        }
    )
    assert outcome.ok is False
    assert outcome.code == "SOURCE_FIELD_NOT_SUPPORTED"


# ---------------------------------------------------------------------------
# Haftalık program (§16-§20/§32/§33)
# ---------------------------------------------------------------------------


def _block(**overrides) -> dict:
    payload = {
        "title": "Veri Yapıları",
        "day_of_week": "monday",
        "start_time": "09:00",
        "end_time": "11:00",
        "source_excerpt": "Pazartesi 09:00-11:00 Veri Yapıları",
    }
    payload.update(overrides)
    return payload


def test_schedule_accepts_source_matching_block() -> None:
    assert _schedule(_block()).ok is True


def test_schedule_weekday_must_match_source() -> None:
    """§97: kaynak Pazartesi, model Cuma diyorsa reddedilir."""
    outcome = _schedule(_block(day_of_week="friday"))
    assert outcome.ok is False
    assert outcome.code == "INVALID_TIME"


def test_schedule_start_time_must_match_source() -> None:
    outcome = _schedule(_block(start_time="14:00"))
    assert outcome.ok is False
    assert outcome.code == "INVALID_TIME"


def test_schedule_end_time_must_match_source() -> None:
    outcome = _schedule(_block(end_time="16:00"))
    assert outcome.ok is False
    assert outcome.code == "INVALID_TIME"


def test_schedule_rejects_when_source_has_no_weekday() -> None:
    outcome = _schedule(
        _block(source_excerpt="09:00-11:00 Veri Yapıları"),
        "09:00-11:00 Veri Yapıları\n",
    )
    assert outcome.ok is False
    assert outcome.code == "INVALID_TIME"


def test_schedule_rejects_when_source_has_no_times() -> None:
    outcome = _schedule(
        _block(source_excerpt="Pazartesi Veri Yapıları"),
        "Pazartesi Veri Yapıları\n",
    )
    assert outcome.ok is False
    assert outcome.code == "INVALID_TIME"


def test_schedule_rejects_ambiguous_weekday() -> None:
    """§18: çakışan gün varsa tahmin edilmez."""
    outcome = _schedule(
        _block(source_excerpt="Pazartesi 09:00-11:00, Cuma 14:00-16:00 Veri Yapıları"),
        "Pazartesi 09:00-11:00, Cuma 14:00-16:00 Veri Yapıları\n",
    )
    assert outcome.ok is False
    assert outcome.code == "INVALID_TIME"


def test_schedule_still_rejects_reversed_times() -> None:
    outcome = _schedule(
        _block(start_time="11:00", end_time="09:00", source_excerpt="Pazartesi 11:00-09:00 Veri Yapıları"),
        "Pazartesi 11:00-09:00 Veri Yapıları\n",
    )
    assert outcome.ok is False
    assert outcome.code == "INVALID_TIME"


def test_english_schedule_block_is_grounded() -> None:
    text = "Wednesday 14:00-16:30 Reading Group\n"
    good = _schedule(
        {
            "title": "Reading Group",
            "day_of_week": "wednesday",
            "start_time": "14:00",
            "end_time": "16:30",
            "source_excerpt": "Wednesday 14:00-16:30 Reading Group",
        },
        text,
    )
    assert good.ok is True


# ---------------------------------------------------------------------------
# Servis düzeyinde uçtan uca (§26)
# ---------------------------------------------------------------------------


async def test_service_rejects_hallucinated_normalized_date_end_to_end(monkeypatch) -> None:
    """Model uydurma tarih döndürürse zincir tükenir ve `needs_escalation` olur."""
    from app.config import settings
    from app.integrations.local_cognition import models as lc
    from tests.h4_test_provider import ScriptedProvider
    from tests.test_h4_service import _run

    monkeypatch.setattr(settings, "h4_enabled", True)
    hallucinated = json.dumps(
        {
            "events": [
                {
                    "title": "Kayıt yenileme",
                    "category": "registration",
                    "date_text": "1 - 5 Eylül 2026",
                    "start_date": "2030-01-01",
                    "end_date": "2030-01-05",
                    "source_excerpt": "Kayıt yenileme: 1 - 5 Eylül 2026",
                }
            ]
        }
    )
    provider = ScriptedProvider(responses=[hallucinated, hallucinated, hallucinated])
    request = lc.build_lane_request(
        lane="structured_extract", text=CALENDAR_TEXT, contract="academic_calendar_v1"
    )

    response = await _run(request, provider)

    assert response.status == "needs_escalation"
    assert all(
        attempt.failure_code == "INVALID_DATE" for attempt in response.route_decision.attempts
    )
    assert response.result is None


async def test_service_accepts_grounded_extraction(monkeypatch) -> None:
    from app.config import settings
    from app.integrations.local_cognition import models as lc
    from tests.h4_test_provider import ScriptedProvider
    from tests.test_h4_service import _run

    monkeypatch.setattr(settings, "h4_enabled", True)
    grounded = json.dumps(
        {
            "events": [
                {
                    "title": "Kayıt yenileme",
                    "category": "registration",
                    "date_text": "1 - 5 Eylül 2026",
                    "start_date": "2026-09-01",
                    "end_date": "2026-09-05",
                    "source_excerpt": "Kayıt yenileme: 1 - 5 Eylül 2026",
                }
            ]
        }
    )
    request = lc.build_lane_request(
        lane="structured_extract", text=CALENDAR_TEXT, contract="academic_calendar_v1"
    )

    response = await _run(request, ScriptedProvider(responses=[grounded]))

    assert response.status == "success"
    assert response.result.items[0]["start_date"] == "2026-09-01"
