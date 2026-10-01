"""Closed canonical metric providers. No SQL/HTTP/expression supplied by clients."""

from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import or_, select

from app.core.models import Entity
from app.modules.goal.models import GoalMilestone
from app.modules.goal.strategy_schemas import Measurement, ProviderMetadata, Reason
from app.modules.learning.models import StudyTopic
from app.modules.opportunity.lifecycle import APPLICATION_FLOW
from app.modules.opportunity.models import Application, ApplicationHistory

PROVIDERS = [
    ProviderMetadata(
        key="manual",
        label="Elle ölçüm",
        description="Kaydedilmiş değer. Otuz gün sonra bayat kanıt uyarısı.",
    ),
    ProviderMetadata(
        key="applications_applied",
        label="Başvuruya ulaşan kayıtlar",
        description="applied durumuna ulaşmış kanonik başvurular; hazırlanıyor kayıtları sayılmaz. Nitelik/uygunluk çıkarımı yapılmaz.",
    ),
    ProviderMetadata(
        key="applications_interview",
        label="Görüşmeye ulaşan kayıtlar",
        description="interview durumuna ulaşmış başvurular; güncel durum ve kanonik geçiş geçmişi.",
    ),
    ProviderMetadata(
        key="applications_offer",
        label="Teklife ulaşan kayıtlar",
        description="offer durumuna ulaşmış başvurular; kabul/uygunluk anlamına gelmez.",
    ),
    ProviderMetadata(
        key="goal_milestones",
        label="Tamamlanan hedef adımları",
        description="Yalnızca açıkça seçildiğinde bu hedefin tamamlanan milestone sayısı.",
    ),
    ProviderMetadata(
        key="linked_completion",
        label="Bağlı kaydın tamamlanması",
        description="Kanonik hedef adımı veya öğrenme konusu: tamamlandıysa 1, değilse 0.",
    ),
]


def numeric_progress(current, baseline, target):
    if current is None:
        return None
    delta = Decimal(target) - Decimal(baseline)
    if delta == 0:
        raise ValueError("Invalid denominator")
    return max(Decimal(0), min(Decimal(1), (Decimal(current) - Decimal(baseline)) / delta))


def trajectory(progress, model, start, target, now):
    if model == "none":
        return "not_applicable", None
    if progress is None or not target:
        return "unknown", None
    if model == "deadline":
        if now < target:
            return "not_applicable", None
        return ("on_track" if progress >= 1 else "behind"), Decimal(1)
    if not start or target <= start:
        return "unknown", None
    expected = max(
        Decimal(0),
        min(
            Decimal(1),
            Decimal(str((now - start).total_seconds()))
            / Decimal(str((target - start).total_seconds())),
        ),
    )
    gap = progress - expected
    return (
        "ahead" if gap > Decimal("0.10") else "behind" if gap < Decimal("-0.10") else "on_track"
    ), expected


class MetricContext:
    """One bounded bulk acquisition per overview, no query per KR."""

    def __init__(self, applications, histories, milestones, topics, truncated=False):
        self.applications, self.histories, self.milestones, self.topics = (
            applications,
            histories,
            milestones,
            topics,
        )
        self.truncated = truncated

    @classmethod
    async def load(cls, session, goal_ids, linked_ids):
        rows = list(
            (
                await session.execute(
                    select(Application, Entity)
                    .join(Entity, Entity.id == Application.opportunity_id)
                    .where(Entity.archived_at.is_(None))
                    .order_by(Application.opportunity_id)
                    .limit(5001)
                )
            ).all()
        )
        histories = list(
            (
                await session.scalars(
                    select(ApplicationHistory)
                    .where(
                        ApplicationHistory.opportunity_id.in_(
                            [row.opportunity_id for row, _ in rows[:5000]]
                        ),
                        ApplicationHistory.scope == "application",
                    )
                    .order_by(ApplicationHistory.id)
                    .limit(20001)
                )
            ).all()
        )
        milestones = list(
            (
                await session.scalars(
                    select(GoalMilestone)
                    .where(
                        or_(GoalMilestone.goal_id.in_(goal_ids), GoalMilestone.id.in_(linked_ids))
                    )
                    .order_by(GoalMilestone.id)
                    .limit(5001)
                )
            ).all()
        )
        topics = list(
            (await session.scalars(select(StudyTopic).where(StudyTopic.id.in_(linked_ids)))).all()
        )
        return cls(
            rows[:5000],
            histories[:20000],
            milestones[:5000],
            topics,
            len(rows) > 5000 or len(histories) > 20000 or len(milestones) > 5000,
        )

    def read(self, kr, now):
        refs, reasons = [], []
        confidence = "high"
        if kr.source_key == "manual":
            current = kr.manual_value
            confidence = "medium"
            refs = [f"entity:{kr.id}"]
            reasons.append(
                Reason(
                    code="MANUAL_VALUE",
                    explanation="Kullanıcının kaydettiği ölçüm; otomatik doğrulanmaz.",
                )
            )
            if not kr.measured_at or now - kr.measured_at > timedelta(days=30):
                confidence = "low"
                reasons.append(
                    Reason(
                        code="STALE_MANUAL",
                        explanation="Ölçüm otuz gündür güncellenmedi veya henüz kaydedilmedi.",
                    )
                )
        elif kr.source_key.startswith("applications_"):
            state = {
                "applications_applied": "applied",
                "applications_interview": "interview",
                "applications_offer": "offer",
            }.get(kr.source_key)
            if state not in APPLICATION_FLOW:
                raise ValueError("Unsupported lifecycle metric")
            reached = {h.opportunity_id for h in self.histories if h.to_status == state}
            states = {state}
            since = kr.source_config.get("since")
            since = datetime.fromisoformat(since) if since else None
            matches = [
                a
                for a, _ in self.applications
                if (not since or a.created_at >= since)
                and (a.status in states or a.opportunity_id in reached)
            ]
            current = Decimal(len(matches))
            refs = [f"entity:{a.opportunity_id}" for a in matches[:100]]
            reasons.append(
                Reason(
                    code="CANONICAL_LIFECYCLE",
                    explanation="Kanonik başvuru durumu/geçiş geçmişinden hesaplandı; uygunluk çıkarımı yapılmadı.",
                )
            )
        elif kr.source_key == "goal_milestones":
            matches = [m for m in self.milestones if m.goal_id == kr.goal_id and m.completed_at]
            current = Decimal(len(matches))
            refs = [f"entity:{m.id}" for m in matches[:100]]
        elif kr.source_key == "linked_completion":
            linked_id = str(kr.source_config.get("linked_entity_id"))
            match = next((m for m in self.milestones if str(m.id) == linked_id), None)
            topic = next((t for t in self.topics if str(t.id) == linked_id), None)
            if match:
                current = Decimal(int(match.completed_at is not None))
            elif topic:
                current = Decimal(int(topic.status == "done"))
            else:
                current = None
            refs = [f"entity:{linked_id}"] if match or topic else []
        else:
            current = None
        if self.truncated and kr.source_key != "manual":
            current, confidence = None, "low"
            reasons.append(
                Reason(
                    code="METRIC_COLLECTION_TRUNCATED",
                    explanation="Kanonik kaynak koleksiyonu sınırı aşıldı; eksik sayım sonuç olarak sunulmadı.",
                )
            )
        if current is None:
            confidence = "low"
            reasons.append(
                Reason(
                    code="MEASUREMENT_UNAVAILABLE",
                    explanation="Ölçüm kaynağı kullanılamıyor veya değer kaydedilmedi.",
                )
            )
        progress = numeric_progress(current, kr.baseline_value, kr.target_value)
        pace, expected = trajectory(progress, kr.trajectory_model, kr.start_at, kr.target_at, now)
        return Measurement(
            current_value=current,
            progress_percent=round(progress * 100) if progress is not None else None,
            expected_percent=round(expected * 100) if expected is not None else None,
            trajectory=pace,
            confidence=confidence,
            reasons=reasons,
            evidence_refs=refs,
        )
