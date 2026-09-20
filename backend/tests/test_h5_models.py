"""H5 sözleşmeleri: mod doğrulaması, zaman semantiği, sınırlar, kimlikler."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from app.integrations.review_intelligence import models as ri
from app.integrations.review_intelligence import policy as policy_svc
from app.integrations.review_intelligence import sources as source_svc


def _names(schema: dict) -> set[str]:
    names: set[str] = set()

    def walk(node: object) -> None:
        if isinstance(node, dict):
            properties = node.get("properties")
            if isinstance(properties, dict):
                names.update(properties.keys())
                for value in properties.values():
                    walk(value)
            for key in ("items", "anyOf", "allOf", "oneOf", "$defs"):
                if key in node:
                    walk(node[key])
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(schema)
    return names


def test_exactly_five_modes() -> None:
    assert ri.ACTIVE_MODES == (
        "continuity",
        "daily_close",
        "weekly_review",
        "period_delta",
        "consolidation_review",
    )


def test_unknown_mode_is_rejected() -> None:
    with pytest.raises(ri.ReviewIntelligenceError, match="INVALID_MODE"):
        policy_svc.validate_mode("monthly_review")
    with pytest.raises(ri.ReviewIntelligenceError, match="INVALID_MODE"):
        policy_svc.validate_mode("project_resume")


@pytest.mark.parametrize(
    ("mode", "provided"),
    [
        ("daily_close", {"since"}),
        ("daily_close", {"until"}),
        ("weekly_review", {"since"}),
        ("continuity", {"reference_date"}),
        ("period_delta", {"reference_date"}),
        # period_delta bilgi alanı TAŞIMAZ: bayrak kabul edilseydi sessizce
        # yok sayılırdı (§124).
        ("period_delta", {"include_knowledge"}),
    ],
)
def test_mode_incompatible_arguments_are_rejected(mode: str, provided: set[str]) -> None:
    """§21/§124: uyumsuz argüman sessizce YOK SAYILMAZ."""
    with pytest.raises(ri.ReviewIntelligenceError, match="INVALID_ARGUMENT"):
        policy_svc.validate_mode_arguments(mode, provided)


def test_mode_compatible_arguments_are_accepted() -> None:
    policy_svc.validate_mode_arguments("continuity", {"since", "until", "focus_entity_id"})
    policy_svc.validate_mode_arguments("weekly_review", {"reference_date", "include_knowledge"})
    policy_svc.validate_mode_arguments("period_delta", {"since", "until"})
    # `include_knowledge` etkili olduğu HER modda kabul edilir.
    for mode in ("continuity", "daily_close", "weekly_review", "consolidation_review"):
        policy_svc.validate_mode_arguments(mode, {"include_knowledge"})


def test_timezone_naive_timestamps_are_rejected() -> None:
    """§22: naif damga reddedilir; sessiz yerel saat varsayımı YOK."""
    with pytest.raises(ri.ReviewIntelligenceError, match="INVALID_TIME_RANGE"):
        source_svc.parse_aware("2026-09-20T10:00:00", "since")
    assert source_svc.parse_aware("2026-09-20T10:00:00+03:00", "since") is not None
    assert source_svc.parse_aware("2026-09-20T10:00:00Z", "since") is not None


def test_invalid_reference_date_is_rejected() -> None:
    with pytest.raises(ri.ReviewIntelligenceError, match="INVALID_REFERENCE_DATE"):
        source_svc.parse_reference_date("20-09-2026")
    assert source_svc.parse_reference_date("2026-09-20") == date(2026, 9, 20)


def test_period_bounds_are_enforced() -> None:
    """§23: özel dönem en fazla 31 gün."""
    now = datetime(2026, 9, 20, 18, 0, tzinfo=UTC)
    with pytest.raises(ri.ReviewIntelligenceError, match="PERIOD_TOO_LARGE"):
        source_svc.resolve_period(
            mode="period_delta",
            since=now - timedelta(days=60),
            until=None,
            reference_date=None,
            now=now,
        )
    period = source_svc.resolve_period(
        mode="period_delta", since=now - timedelta(days=10), until=None, reference_date=None, now=now
    )
    assert period.days == 10
    assert period.partial is True


def test_period_delta_requires_since() -> None:
    with pytest.raises(ri.ReviewIntelligenceError, match="INVALID_ARGUMENT"):
        source_svc.resolve_period(
            mode="period_delta", since=None, until=None, reference_date=None, now=datetime.now(UTC)
        )


def test_local_calendar_days_do_not_drift_with_timezone() -> None:
    """Regresyon: UTC `.date()` Europe/Istanbul'da bir gün kaydırıyordu."""
    now = datetime(2026, 9, 20, 18, 0, tzinfo=UTC)
    daily = source_svc.resolve_period(
        mode="daily_close", since=None, until=None, reference_date=date(2026, 9, 18), now=now
    )
    assert daily.start_day == date(2026, 9, 18)
    assert daily.end_day == date(2026, 9, 19)
    assert source_svc.daily_note_days(daily.start_day, daily.end_day) == [date(2026, 9, 18)]

    weekly = source_svc.resolve_period(
        mode="weekly_review", since=None, until=None, reference_date=date(2026, 9, 20), now=now
    )
    assert weekly.start_day == date(2026, 9, 14)
    assert len(source_svc.daily_note_days(weekly.start_day, weekly.end_day)) == 7


def test_candidate_ids_are_deterministic_and_content_addressed() -> None:
    """§59: kimlik vermek için aday SAKLANMAZ."""
    first = policy_svc.candidate_id("decision", "Minimum kaynak UI", ["vault:a.md:L1-L2"])
    second = policy_svc.candidate_id("decision", "  minimum   kaynak ui ", ["vault:a.md:L1-L2"])
    third = policy_svc.candidate_id("decision", "Minimum kaynak UI", ["vault:b.md:L3-L4"])

    assert first == second  # normalize metin aynı
    assert first != third  # destek ref'i farklı
    assert first.startswith("cand_")


def test_destination_policy_is_a_suggestion_table() -> None:
    assert policy_svc.destination_for("commitment", entity_scoped=False) == "todo"
    assert policy_svc.destination_for("goal", entity_scoped=False) == "hot_memory"
    assert policy_svc.destination_for("constraint", entity_scoped=False) == "hot_memory"
    assert policy_svc.destination_for("decision", entity_scoped=True) == "project_vault"
    assert policy_svc.destination_for("decision", entity_scoped=False) == "general_vault"


def test_attention_reasons_are_ordered_without_scores() -> None:
    assert policy_svc.attention_rank("overdue") < policy_svc.attention_rank("deadline_1d")
    assert policy_svc.attention_rank("deadline_1d") < policy_svc.attention_rank("deadline_3d")
    assert policy_svc.attention_rank("deadline_3d") < policy_svc.attention_rank("unread_accumulation")
    assert policy_svc.deadline_reason(0) == "deadline_1d"
    assert policy_svc.deadline_reason(2) == "deadline_3d"
    assert policy_svc.deadline_reason(6) == "deadline_7d"


def test_no_confidence_or_productivity_fields_anywhere() -> None:
    """§37/§102/§141: puan, olasılık, üretkenlik notu YOK."""
    forbidden = {
        "confidence",
        "probability",
        "truth_score",
        "importance",
        "attention_debt",
        "productivity",
        "discipline",
        "alignment",
        "mood",
        "life_score",
    }
    names = _names(ri.ReviewIntelligenceResponse.model_json_schema())
    assert not (names & forbidden)


def test_every_warning_code_has_a_production_path() -> None:
    """Ölü sözleşme yok: tanımlı her kod kod içinde ÜRETİLİYOR olmalı."""
    import pathlib as _pathlib
    from typing import get_args

    codes = set(get_args(ri.WarningCode))
    source = "\n".join(
        item.read_text(encoding="utf-8")
        for item in _pathlib.Path("app/integrations/review_intelligence").glob("*.py")
        if item.name != "models.py"
    )
    emitted = {code for code in codes if f'"{code}"' in source}
    assert emitted == codes, sorted(codes - emitted)


def test_warning_and_ref_bounds_are_declared() -> None:
    collector = ri.Collector()
    for index in range(ri.MAX_H5_WARNINGS + 5):
        collector.warn("EVENT_SCAN_TRUNCATED", f"deneme {index}")
    assert len(collector.warnings) == ri.MAX_H5_WARNINGS
    assert all(len(warning) <= ri.MAX_WARNING_CHARS for warning in collector.warnings)


def test_response_payload_is_typed_per_mode() -> None:
    schema = ri.ReviewIntelligenceResponse.model_json_schema()
    assert "payload" in schema["properties"]
    dumped = str(schema)
    for bundle in ("ContinuityBundle", "DailyCloseBundle", "WeeklyReviewBundle", "PeriodDeltaBundle", "ConsolidationBundle"):
        assert bundle in dumped


def test_review_insight_requires_a_canonical_source() -> None:
    """§H5.1: KAYNAKSIZ OLGU GEÇERSİZDİR — kural model düzeyinde zorlanır."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ri.ReviewInsight(
            type="win",
            text="Tamamlandı: kaynaksız görev",
            support_refs=[],
            source_count=0,
            status="fact",
        )
    # Aday da kaynaksız olamaz: H5 desteksiz aday ÜRETMEZ.
    with pytest.raises(ValidationError):
        ri.ReviewInsight(type="change", text="x", support_refs=[], status="candidate")
    # Yalnızca boşluk içeren referans "referans" sayılmaz.
    with pytest.raises(ValidationError):
        ri.ReviewInsight(type="win", text="x", support_refs=["   "], status="fact")
    # Boş referans karışık listede de sessizce kabul edilmez.
    with pytest.raises(ValidationError):
        ri.ReviewInsight(type="win", text="x", support_refs=["event:1", ""], status="fact")

    accepted = ri.ReviewInsight(
        type="win", text="Tamamlandı: görev", support_refs=["event:42"], source_count=1, status="fact"
    )
    assert accepted.support_refs == ["event:42"]


def test_review_insight_citation_field_is_required() -> None:
    """Alan varsayılana düşemez: kaynak vermek ZORUNLUDUR."""
    assert ri.ReviewInsight.model_fields["support_refs"].is_required()


def test_source_count_is_derived_from_citations() -> None:
    """§H5.2: sayaç kanıt listesinden TÜRETİLİR; çelişki imkânsızdır."""
    one = ri.ReviewInsight(type="win", text="x", support_refs=["event:1"])
    assert one.source_count == 1

    # Açıkça yanlış sayaç geçmek etkisizdir: türetim kazanır.
    two = ri.ReviewInsight(
        type="win", text="x", support_refs=["event:1", "entity:2"], source_count=99
    )
    assert two.source_count == 2

    # Kopya referans İKİ KEZ sayılmaz; deterministik olarak tekilleşir.
    duplicate = ri.ReviewInsight(type="win", text="x", support_refs=["event:1", "event:1"])
    assert duplicate.support_refs == ["event:1"]
    assert duplicate.source_count == 1

    # Sıra KARARLIDIR: ilk görülme sırası korunur.
    stable = ri.ReviewInsight(type="win", text="x", support_refs=["b", "a", "b"])
    assert stable.support_refs == ["b", "a"]
    assert stable.source_count == 2

    # Boşluk kırpılır, kopya sayılmaz.
    trimmed = ri.ReviewInsight(type="win", text="x", support_refs=[" event:7 ", "event:7"])
    assert trimmed.support_refs == ["event:7"]
    assert trimmed.source_count == 1


def test_source_count_cannot_disagree_after_roundtrip() -> None:
    """Serileştirme sonrası da tutarlı: doğrulama türetimi yeniden uygular."""
    insight = ri.ReviewInsight(type="win", text="x", support_refs=["event:1", "entity:2"])
    payload = insight.model_dump()
    payload["source_count"] = 0  # düşmanca/bozuk yük
    restored = ri.ReviewInsight.model_validate(payload)
    assert restored.source_count == len(restored.support_refs) == 2
