"""H5 gözden geçirme zekâsı (review intelligence) sözleşmeleri.

H5, var olan kanonik kaynakların üzerinde **sınırlı, salt-okunur** bir yansıma
katmanıdır: süreklilik (nerede kalmıştım), delta (ne değişti), gözden geçirme ve
konsolidasyon **adayları**.

Değişmez ayrımlar (§14/§93/§179):

```text
FACT       kaynaktan doğrulanabilen olgu (support_refs zorunlu)
CANDIDATE  kaynağa dayanan ama doğruluğu iddia edilmeyen öneri
SUGGESTION yalnızca Hermes'in ürettiği yorum (H5 üretmez)
```

```text
episodic  != semantic      (Event/Günlük not → kalıcı bilgi DEĞİL, aday)
candidate != memory        (H2 sahipliği değişmez)
summary   != evidence      (özet kanıt sayılmaz)
Hot Memory != tarihsel kanıt
H4 çıktısı != doğruluk
```

H5 hiçbir şey yazmaz: Entity/Link/Event/Todo/Review/Vault/Sıcak Hafıza
mutasyonu YOKTUR (§16).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Modlar (§17)
# ---------------------------------------------------------------------------

ReviewMode = Literal[
    "continuity",
    "daily_close",
    "weekly_review",
    "period_delta",
    "consolidation_review",
]

ACTIVE_MODES: tuple[str, ...] = (
    "continuity",
    "daily_close",
    "weekly_review",
    "period_delta",
    "consolidation_review",
)

# ---------------------------------------------------------------------------
# Sınırlar (§138)
# ---------------------------------------------------------------------------

MAX_H5_EVENTS_SCAN = 500
MAX_H5_SOURCE_REFS = 100
MAX_H5_INSIGHTS = 30
MAX_H5_OPEN_LOOPS = 20
MAX_H5_DEADLINES = 15
MAX_H5_ATTENTION = 15
MAX_H5_PROMOTIONS = 20
MAX_H5_KNOWLEDGE_HEALTH = 10
MAX_H5_RESURFACE = 3
MAX_H5_WARNINGS = 20
MAX_WARNING_CHARS = 300
MAX_H5_DAILY_NOTE_CHARS = 4000
MAX_H5_DAILY_NOTES = 7
MAX_H5_H4_PACKET_CHARS = 20000
MAX_H5_H4_FRAGMENTS = 12
MAX_H5_H4_CANDIDATE_CALLS = 2
MAX_H5_ACTIVE_THREADS = 10
MAX_H5_PERIOD_DAYS = 31
MAX_H5_SUPERSESSION_CHECKS = 5
MAX_H5_H3_ITEMS_PER_CANDIDATE = 3
MAX_H5_BODY_OF_WORK = 20
MAX_H5_COMPLETED_RECENT = 20
MAX_H5_PRIORITIES = 10

#: Eşikler (§68/§83/§31).
STALLED_PROJECT_DAYS = 14
RESURFACE_AGE_DAYS = 30
UPCOMING_DEADLINE_DAYS = 7
DEADLINE_URGENT_DAYS = 1
DEADLINE_SOON_DAYS = 3
UNREAD_ACCUMULATION_THRESHOLD = 20

#: Girdi sınırları (§20/§22).
MIN_REFERENCE_DATE_LEN = 10
MAX_FOCUS_ENTITY_LEN = 64
MAX_SINCE_LEN = 40

# ---------------------------------------------------------------------------
# Kodlar
# ---------------------------------------------------------------------------

WarningCode = Literal[
    "PARTIAL_PERIOD",
    "MISSING_DAILY_NOTES",
    "VAULT_UNAVAILABLE",
    "EVENT_SCAN_TRUNCATED",
    "NO_PREVIOUS_REVIEW",
    "NO_MEANINGFUL_ACTIVITY",
    "PRIORITY_RECEIPTS_UNAVAILABLE",
    "H4_UNAVAILABLE",
    "SOURCE_PACKET_TRUNCATED",
    "AMBIGUOUS_CANDIDATE_SOURCE",
    "CONFLICTING_KNOWLEDGE",
    "KNOWLEDGE_HEALTH_TRUNCATED",
    "H3_EVIDENCE_UNAVAILABLE",
    "DEADLINE_SCAN_TRUNCATED",
]

ReviewErrorCode = Literal[
    "INVALID_MODE",
    "INVALID_ARGUMENT",
    "INVALID_TIME_RANGE",
    "INVALID_REFERENCE_DATE",
    "INVALID_FOCUS_ENTITY",
    "PERIOD_TOO_LARGE",
]

#: Kaynak alanları (§88).
SourceDomain = Literal["operational", "review", "vault", "evidence", "aggregate"]

#: Insight tipi ve durumu (§95).
InsightType = Literal[
    "change",
    "win",
    "open_loop",
    "risk",
    "stalled",
    "time_sensitive",
    "knowledge_health",
]
InsightStatus = Literal["fact", "candidate"]

#: Süreklilik çapası (§27).
AnchorKind = Literal["explicit", "last_meaningful_activity", "previous_review", "fallback"]

#: Konsolidasyon aday türleri (§54).
CandidateKind = Literal[
    "decision",
    "lesson",
    "commitment",
    "goal",
    "constraint",
    "project_knowledge",
    "reference",
]

#: Önerilen varış yeri (§60) — H5 YAZMAZ, yalnızca önerir.
PromotionDestination = Literal["todo", "hot_memory", "project_vault", "general_vault"]

#: Var olan Todo ile eşleşme durumu (§67).
MatchState = Literal["exact_match", "no_exact_match", "unknown"]

#: Bilgi sağlığı sorun tipleri (§72).
KnowledgeIssue = Literal[
    "possibly_stale",
    "possibly_superseded",
    "possibly_conflicting",
    "managed_source_conflict",
]

#: Dikkat adayı gerekçe kodları (§38) — opak puan YOKTUR.
AttentionReason = Literal[
    "overdue",
    "deadline_1d",
    "deadline_3d",
    "deadline_7d",
    "passed_plan_open",
    "unread_accumulation",
    "project_without_next_action",
    "project_inactive",
]

#: İz adımları (§98).
TraceStep = Literal[
    "period_resolved",
    "review_preview_loaded",
    "previous_review_loaded",
    "events_loaded",
    "daily_notes_loaded",
    "deadlines_loaded",
    "projects_checked",
    "h3_evidence_loaded",
    "h4_candidates_extracted",
    "knowledge_health_checked",
    "budget_applied",
]

# ---------------------------------------------------------------------------
# Kaynak ve kapsam
# ---------------------------------------------------------------------------


class SourceRef(BaseModel):
    """İncelenebilir kaynak referansı (§88/§89).

    Deterministik ve tekrarlanabilirdir; mutlak dosya yolu taşımaz.
    """

    ref: str = Field(..., description="Deterministik referans, ör. 'event:12345' veya 'vault:10 Daily/….md:L12-L18'.")
    domain: SourceDomain
    kind: str = Field(..., description="Kaynak türü, ör. 'event', 'review', 'daily_note', 'aggregate'.")
    title: str | None = None
    timestamp: str | None = None
    entity_id: str | None = None
    evidence_id: str | None = None
    locator: str | None = Field(default=None, description="Dosya içi konum (göreli yol + satır aralığı).")
    excerpt: str | None = Field(default=None, description="Sınırlı kaynak alıntısı.")
    truncated: bool = False


class Coverage(BaseModel):
    """Dönem kapsamı ve dürüstlük bayrakları (§47/§97)."""

    period_start: str = Field(..., description="ISO-8601, saat dilimli.")
    period_end: str = Field(..., description="ISO-8601, saat dilimli (hariç).")
    days: int = Field(..., ge=0)
    partial: bool = Field(default=False, description="Dönem henüz tamamlanmadı.")
    comparable: bool = Field(default=True, description="Tam dönemlerle sayısal karşılaştırma yapılabilir mi.")
    reference_date: str | None = None


class ContinuityAnchor(BaseModel):
    """Süreklilik çapası (§27) — uydurma 'son kez' YOKTUR."""

    kind: AnchorKind
    timestamp: str = Field(..., description="ISO-8601, saat dilimli.")
    source_ref: str | None = None
    entity_id: str | None = None
    verb: str | None = None


# ---------------------------------------------------------------------------
# Olgular ve adaylar
# ---------------------------------------------------------------------------


class ReviewInsight(BaseModel):
    """Kaynağa bağlı tek bir gözlem (§95).

    KANIT KİLİDİ (§90/H5.1): her `ReviewInsight` en az bir KANONİK kaynak
    referansı taşır. Kaynaksız olgu uydurma olurdu; bu yüzden kural yalnızca
    `status=fact` için değil, model düzeyinde ZORUNLUDUR. Boş ya da yalnızca
    boşluk içeren referans listesi doğrulama hatasıdır: fail-closed.
    """

    type: InsightType
    text: str
    support_refs: list[str]
    source_count: int = Field(default=0, ge=0)
    temporal_start: str | None = None
    temporal_end: str | None = None
    status: InsightStatus = "fact"

    @field_validator("support_refs")
    @classmethod
    def _require_canonical_citation(cls, value: list[str]) -> list[str]:
        refs = [ref for ref in value if ref and ref.strip()]
        if not refs:
            raise ValueError("support_refs requires at least one canonical source ref")
        if len(refs) != len(value):
            raise ValueError("support_refs must not contain blank refs")
        return refs


class AttentionCandidate(BaseModel):
    """Dikkat adayı — sıralama ve gerekçe koddadır, puan YOKTUR (§37/§38)."""

    reason: AttentionReason
    text: str
    support_refs: list[str] = Field(default_factory=list)
    entity_id: str | None = None
    due_at: str | None = None
    remaining_days: int | None = None


class CanonicalOpenLoop(BaseModel):
    """Kanonik olarak AÇIK olan döngü (§127) — olgu."""

    kind: Literal["todo", "project_next_action", "application", "deadline", "milestone"]
    title: str
    entity_id: str | None = None
    detail: str | None = None
    due_at: str | None = None
    support_refs: list[str] = Field(default_factory=list)


class PossibleOpenLoop(BaseModel):
    """Model kaynaklı olası açık döngü (§65-§67) — kanonik Todo DEĞİL."""

    text: str
    support_refs: list[str] = Field(default_factory=list)
    matching_todo_id: str | None = None
    match_state: MatchState = "unknown"


class PromotionCandidate(BaseModel):
    """Kalıcı bilgiye terfi ADAYI (§58) — skor yok, öneri var."""

    candidate_id: str = Field(..., description="Deterministik: kind + normalize metin + destek ref'leri.")
    kind: CandidateKind
    text: str
    suggested_destination: PromotionDestination = Field(
        ..., description="Politika önerisi; H5 buraya YAZMAZ (§60)."
    )
    support_refs: list[str] = Field(default_factory=list)
    source_count: int = Field(default=0, ge=0)
    recurrence_count: int = Field(default=1, ge=1)
    status: Literal["candidate", "already_present"] = "candidate"
    warnings: list[str] = Field(default_factory=list)


class KnowledgeHealthCandidate(BaseModel):
    """Bilgi sağlığı adayı (§72) — otomatik geçersiz kılma YOKTUR."""

    issue: KnowledgeIssue
    reason: str = Field(..., description="Sınırlı, olgusal gerekçe kodu/metni.")
    text: str
    support_refs: list[str] = Field(default_factory=list)
    source_count: int = Field(default=0, ge=0)
    entity_id: str | None = None
    warnings: list[str] = Field(default_factory=list)


class ResurfaceCandidate(BaseModel):
    """Yapısal olarak ilgili, eskimiş bilgi (§83/§84) — rastgele not değil."""

    ref: str
    title: str
    age_days: int = Field(..., ge=0)
    related_entity_id: str | None = None
    reasons: list[str] = Field(default_factory=list)


class SourceManifest(BaseModel):
    """H5 gerçekte NEYE baktı (§96/§97)."""

    events_considered: int = 0
    reviews_considered: int = 0
    entities_considered: int = 0
    projects_considered: int = 0
    deadlines_considered: int = 0
    daily_notes_expected: int = 0
    daily_notes_found: int = 0
    daily_notes_missing: int = 0
    vault_sources: list[str] = Field(default_factory=list)
    h3_evidence_ids: list[str] = Field(default_factory=list)
    hot_memory_checked: int = 0
    h4_used: bool = False
    truncated: bool = False


class TraceStepRecord(BaseModel):
    """Sınırlı olgusal iz adımı (§98) — düşünme zinciri DEĞİL."""

    step: TraceStep
    considered: int = Field(default=0, ge=0)
    accepted: int = Field(default=0, ge=0)
    truncated: bool = False


class ThreadRef(BaseModel):
    """Süreklilikte önerilen sınırlı iş parçası (§126)."""

    kind: Literal["learning", "focus", "project", "todo", "deadline", "application", "knowledge"]
    title: str
    entity_id: str | None = None
    detail: str | None = None
    support_refs: list[str] = Field(default_factory=list)


class LearningResume(BaseModel):
    """Öğrenme/odak bağlamına dönüş için olgusal zemin (§40)."""

    topic: str | None = None
    minutes: int | None = None
    last_activity_at: str | None = None
    related_todo_id: str | None = None
    study_area: str | None = None
    support_refs: list[str] = Field(default_factory=list)


class UnreadAccumulation(BaseModel):
    """Okunmamış birikimi (§33) — yüzlerce başlık dökülmez."""

    new_unread_since_anchor: int = Field(default=0, ge=0)
    current_unread_total: int = Field(default=0, ge=0)
    top_sources: list[dict] = Field(default_factory=list, description="Sınırlı kaynak/kategori kırılımı.")
    support_refs: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Mod paketleri
# ---------------------------------------------------------------------------


class ContinuityBundle(BaseModel):
    """Süreklilik paketi (§28). Her alan dolu olmak zorunda değildir."""

    anchor: ContinuityAnchor
    activity_gap_hours: float = Field(default=0.0, ge=0)
    last_meaningful_activity: dict | None = None
    recent_completed: list[ReviewInsight] = Field(default_factory=list)
    state_changes: list[ReviewInsight] = Field(default_factory=list)
    time_sensitive_changes: list[ReviewInsight] = Field(default_factory=list)
    newly_overdue: list[CanonicalOpenLoop] = Field(default_factory=list)
    upcoming_deadlines: list[dict] = Field(default_factory=list)
    unread_accumulation: UnreadAccumulation = Field(default_factory=UnreadAccumulation)
    passed_plans_still_open: list[CanonicalOpenLoop] = Field(default_factory=list)
    open_loops: list[CanonicalOpenLoop] = Field(default_factory=list)
    active_threads: list[ThreadRef] = Field(default_factory=list)
    learning_resume: LearningResume | None = None
    stalled_projects: list[ReviewInsight] = Field(default_factory=list)
    attention_candidates: list[AttentionCandidate] = Field(default_factory=list)
    knowledge_changes: list[ReviewInsight] = Field(default_factory=list)
    resurface_candidates: list[ResurfaceCandidate] = Field(default_factory=list)
    focus_entity: dict | None = None


class DailyCloseBundle(BaseModel):
    """Gün kapanışı (§49)."""

    day: str
    review_preview: dict | None = None
    completed_outcomes: list[ReviewInsight] = Field(default_factory=list)
    focus_summary: dict = Field(default_factory=dict)
    open_todos: list[CanonicalOpenLoop] = Field(default_factory=list)
    newly_overdue: list[CanonicalOpenLoop] = Field(default_factory=list)
    upcoming: list[dict] = Field(default_factory=list)
    open_loops: list[CanonicalOpenLoop] = Field(default_factory=list)
    promotion_candidates: list[PromotionCandidate] = Field(default_factory=list)
    carry_forward_candidates: list[CanonicalOpenLoop] = Field(default_factory=list)
    daily_note: dict | None = None


class WeeklyReviewBundle(BaseModel):
    """Haftalık delta gözden geçirmesi (§42)."""

    current_snapshot: dict | None = None
    previous_review: dict | None = None
    comparison: dict = Field(default_factory=dict)
    declared_priorities: list[dict] = Field(default_factory=list)
    priority_outcomes: list[dict] = Field(default_factory=list)
    body_of_work: list[ReviewInsight] = Field(default_factory=list)
    focus_distribution: dict = Field(default_factory=dict)
    changes: list[ReviewInsight] = Field(default_factory=list)
    wins: list[ReviewInsight] = Field(default_factory=list)
    open_loops: list[CanonicalOpenLoop] = Field(default_factory=list)
    stalled_projects: list[ReviewInsight] = Field(default_factory=list)
    upcoming: list[dict] = Field(default_factory=list)
    time_sensitive_changes: list[ReviewInsight] = Field(default_factory=list)
    promotion_candidates: list[PromotionCandidate] = Field(default_factory=list)
    knowledge_health: list[KnowledgeHealthCandidate] = Field(default_factory=list)
    resurface_candidates: list[ResurfaceCandidate] = Field(default_factory=list)
    carry_forward_candidates: list[CanonicalOpenLoop] = Field(default_factory=list)


class PeriodDeltaBundle(BaseModel):
    """İki an arasında ne değişti (§50)."""

    completed: list[ReviewInsight] = Field(default_factory=list)
    created: list[ReviewInsight] = Field(default_factory=list)
    closed: list[ReviewInsight] = Field(default_factory=list)
    opened: list[ReviewInsight] = Field(default_factory=list)
    status_changes: list[ReviewInsight] = Field(default_factory=list)
    focus: dict = Field(default_factory=dict)
    deadline_changes: list[ReviewInsight] = Field(default_factory=list)
    new_announcements: list[ReviewInsight] = Field(default_factory=list)
    applications: list[ReviewInsight] = Field(default_factory=list)
    project_changes: list[ReviewInsight] = Field(default_factory=list)
    open_loops: list[CanonicalOpenLoop] = Field(default_factory=list)
    focus_entity: dict | None = None


class ConsolidationBundle(BaseModel):
    """Konsolidasyon: hangi geçici bilgi kalıcı olmayı hak ediyor (§51/§62)."""

    promotion_candidates: list[PromotionCandidate] = Field(default_factory=list)
    possible_open_loops: list[PossibleOpenLoop] = Field(default_factory=list)
    knowledge_health: list[KnowledgeHealthCandidate] = Field(default_factory=list)
    resurface_candidates: list[ResurfaceCandidate] = Field(default_factory=list)
    daily_notes: list[dict] = Field(default_factory=list)
    source_fragments: int = Field(default=0, ge=0)


ReviewPayload = (
    ContinuityBundle
    | DailyCloseBundle
    | WeeklyReviewBundle
    | PeriodDeltaBundle
    | ConsolidationBundle
)


class ReviewIntelligenceResponse(BaseModel):
    """H5 aracının tek çıktısı (§125).

    Prose DEĞİLDİR: yapı, kaynak ve iz döner; anlatıyı Hermes kurar.
    """

    mode: ReviewMode
    coverage: Coverage
    payload: ReviewPayload
    sources: list[SourceRef] = Field(default_factory=list)
    evidence: list[dict] = Field(default_factory=list, description="H3 EvidenceItem'ları (doğrudan).")
    source_manifest: SourceManifest = Field(default_factory=SourceManifest)
    trace: list[TraceStepRecord] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    truncated: bool = False


@dataclass
class Collector:
    """İÇ toplama kabı — genel sözleşme DEĞİLDİR.

    Modüller kaynak referanslarını, izi, uyarıları ve kapsam sayacını buradan
    paylaşır; böylece her modül aynı sınırları (uyarı sayısı, ref sayısı)
    uygular ve sonuç dürüst kalır.
    """

    sources: list[SourceRef] = field(default_factory=list)
    trace: list[TraceStepRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    manifest: SourceManifest = field(default_factory=SourceManifest)
    truncated: bool = False

    def warn(self, code: str, detail: str | None = None) -> None:
        """Sınırlı uyarı (§99). Tekrarlar birleştirilmez; tavan uygulanır."""
        if len(self.warnings) >= MAX_H5_WARNINGS:
            return
        text = f"{code}: {detail}" if detail else code
        self.warnings.append(text[:MAX_WARNING_CHARS])

    def step(
        self, step: TraceStep, *, considered: int = 0, accepted: int = 0, truncated: bool = False
    ) -> None:
        self.trace.append(
            TraceStepRecord(step=step, considered=considered, accepted=accepted, truncated=truncated)
        )

    def add_source(self, source: SourceRef) -> str:
        """Kaynağı (sınırlı) listeye ekler ve `ref`'ini döner."""
        if len(self.sources) < MAX_H5_SOURCE_REFS:
            self.sources.append(source)
        return source.ref

    def add_evidence(self, items: list[dict]) -> list[str]:
        refs: list[str] = []
        for item in items:
            evidence_id = str(item.get("evidence_id") or "")
            if not evidence_id:
                continue
            if len(self.evidence) < MAX_H5_SOURCE_REFS:
                self.evidence.append(item)
            refs.append(f"h3:{evidence_id}")
        return refs


class ReviewIntelligenceError(Exception):
    """Sınırlı, model-okunur H5 hatası."""

    def __init__(self, code: ReviewErrorCode, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


#: Insight metni ve aday metni için üst sınırlar.
MAX_INSIGHT_TEXT = 400
MAX_CANDIDATE_TEXT = 500
MAX_REF_CHARS = 200


__all__ = [name for name in dir() if not name.startswith("_")]
