from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.todo.schemas import TodoOut

#: Baslik/URL/not tavanlari -- hem CRUD hem import ayni siniri kullanir.
TITLE_MAX = 300
URL_MAX = 2000
NOTE_MAX = 5000

#: Konu durumlari -- uygulamanin TEK kumesi (DB CHECK'i de ayni liste).
TOPIC_STATUSES = ["not_started", "in_progress", "done"]
#: Kurs durumlari -- DB CHECK'i ile ayni.
COURSE_STATUSES = ["planned", "in_progress", "done", "dropped"]
#: Kaynak turleri -- arayuz ikonu/rozeti bunlardan gelir (DB CHECK'i ile ayni).
RESOURCE_KINDS = ["link", "video", "article", "course", "book", "doc", "exercise"]
#: Kaynagin nereden geldigi: elle / yer imi / ice aktarma.
RESOURCE_SOURCES = ["manual", "bookmark", "import"]


def _clean_title(value: str) -> str:
    """Basligi kirpar + ic bosluklari sadelestirir; yalniz bosluksa reddeder."""
    title = " ".join(value.split())
    if not title:
        raise ValueError("baslik bos olamaz")
    return title


def _clean_url(value: str | None) -> str | None:
    if value is None:
        return None
    url = value.strip()
    if not url:
        return None
    if not url.lower().startswith(("http://", "https://")):
        raise ValueError("url http(s) ile baslamali")
    return url


# ---------------------------------------------------------------------------
# Kurslar
# ---------------------------------------------------------------------------


class CourseIn(BaseModel):
    title: str = Field(max_length=TITLE_MAX)
    platform: str | None = Field(default=None, max_length=200)
    url: str | None = Field(default=None, max_length=URL_MAX)
    status: str = "planned"
    progress_pct: int = Field(0, ge=0, le=100)
    notes: str | None = Field(default=None, max_length=NOTE_MAX)
    certificate_entity_id: UUID | None = None
    area_ids: list[UUID] = Field(default_factory=list)
    topic_ids: list[UUID] = Field(default_factory=list)

    _title = field_validator("title")(_clean_title)
    _url = field_validator("url")(_clean_url)

    @field_validator("status")
    @classmethod
    def status_known(cls, v: str) -> str:
        if v not in COURSE_STATUSES:
            raise ValueError(f"status su olmali: {COURSE_STATUSES}")
        return v


class CoursePatch(BaseModel):
    title: str | None = Field(default=None, max_length=TITLE_MAX)
    platform: str | None = Field(default=None, max_length=200)
    url: str | None = Field(default=None, max_length=URL_MAX)
    status: str | None = None
    progress_pct: int | None = Field(None, ge=0, le=100)
    notes: str | None = Field(default=None, max_length=NOTE_MAX)
    certificate_entity_id: UUID | None = None
    area_ids: list[UUID] | None = None
    topic_ids: list[UUID] | None = None
    archived: bool | None = None

    @field_validator("title")
    @classmethod
    def title_clean(cls, v: str | None) -> str | None:
        return _clean_title(v) if v is not None else None

    _url = field_validator("url")(_clean_url)

    @field_validator("status")
    @classmethod
    def status_known(cls, v: str | None) -> str | None:
        if v is not None and v not in COURSE_STATUSES:
            raise ValueError(f"status su olmali: {COURSE_STATUSES}")
        return v


class CourseOut(BaseModel):
    id: UUID
    title: str
    platform: str | None = None
    url: str | None = None
    status: str
    progress_pct: int
    started_at: date | None = None
    completed_at: date | None = None
    certificate_entity_id: UUID | None = None
    notes: str | None = None
    archived: bool = False
    area_ids: list[UUID] = Field(default_factory=list)
    topic_ids: list[UUID] = Field(default_factory=list)
    resource_count: int = 0


# ---------------------------------------------------------------------------
# Calisma alanlari
# ---------------------------------------------------------------------------


class AreaIn(BaseModel):
    title: str = Field(max_length=TITLE_MAX)
    color: str | None = Field(default=None, max_length=32)
    position: int = 0

    _title = field_validator("title")(_clean_title)


class AreaPatch(BaseModel):
    title: str | None = Field(default=None, max_length=TITLE_MAX)
    color: str | None = Field(default=None, max_length=32)
    active: bool | None = None
    position: int | None = None
    archived: bool | None = None

    @field_validator("title")
    @classmethod
    def title_clean(cls, v: str | None) -> str | None:
        return _clean_title(v) if v is not None else None


class StudyAreaOut(BaseModel):
    id: UUID
    title: str
    color: str | None = None
    active: bool = True
    position: int = 0
    archived_at: datetime | None = None
    topic_count: int = 0
    done_count: int = 0
    resource_count: int = 0
    resource_done: int = 0
    focus_minutes: int = 0
    stale_count: int = 0
    last_studied_at: datetime | None = None


# ---------------------------------------------------------------------------
# Konular
# ---------------------------------------------------------------------------


class TopicIn(BaseModel):
    title: str = Field(max_length=TITLE_MAX)
    area_id: UUID
    parent_id: UUID | None = None
    status: str = "not_started"
    confidence: int | None = Field(None, ge=1, le=5)
    target_min: int | None = Field(None, ge=1)
    position: int = 0

    _title = field_validator("title")(_clean_title)

    @field_validator("status")
    @classmethod
    def status_known(cls, v: str) -> str:
        if v not in TOPIC_STATUSES:
            raise ValueError(f"status su olmali: {TOPIC_STATUSES}")
        return v


class TopicPatch(BaseModel):
    title: str | None = Field(default=None, max_length=TITLE_MAX)
    parent_id: UUID | None = None
    status: str | None = None
    confidence: int | None = Field(None, ge=1, le=5)
    target_min: int | None = Field(None, ge=1)
    mastery: int | None = Field(None, ge=0, le=100)
    position: int | None = None

    @field_validator("title")
    @classmethod
    def title_clean(cls, v: str | None) -> str | None:
        return _clean_title(v) if v is not None else None

    @field_validator("status")
    @classmethod
    def status_known(cls, v: str | None) -> str | None:
        if v is not None and v not in TOPIC_STATUSES:
            raise ValueError(f"status su olmali: {TOPIC_STATUSES}")
        return v


class TopicMoveIn(BaseModel):
    parent_id: UUID | None = None
    position: int | None = Field(default=None, ge=0)


class StudyTopicOut(BaseModel):
    id: UUID
    title: str
    area_id: UUID
    parent_id: UUID | None = None
    status: str
    confidence: int | None = None
    target_min: int | None = None
    position: int = 0
    mastery: int | None = None
    last_studied_at: datetime | None = None
    interval_days: int = 0
    ease: float = 2.5
    review_count: int = 0
    last_reviewed_at: datetime | None = None
    next_review_at: datetime | None = None


class TopicProgressOut(BaseModel):
    total: int = 0
    done: int = 0
    pct: int = 0




class TopicStatsDetailOut(BaseModel):
    minutes: int = 0
    sessions: int = 0
    week_minutes: int = 0
    last_studied_at: datetime | None = None


class AncestorOut(BaseModel):
    id: UUID
    title: str


class ReviewBlockOut(BaseModel):
    interval_days: int = 0
    ease: float = 2.5
    review_count: int = 0
    last_reviewed_at: datetime | None = None
    next_review_at: datetime | None = None
    mastery: int | None = None
    due: bool = False


class OpenTodoOut(BaseModel):
    id: UUID
    title: str
    status: str
    plan_day: date | None = None
    priority: int | None = None
    due_at: datetime | None = None


class StudyTopicDetailOut(BaseModel):
    topic: StudyTopicOut
    ancestors: list[AncestorOut] = Field(default_factory=list)
    resources: list[ResourceOut] = Field(default_factory=list)
    progress: TopicProgressOut
    stats: TopicStatsDetailOut
    open_todo: OpenTodoOut | None = None
    flashcard_deck_count: int = 0
    review: ReviewBlockOut


class StudyTopicNode(BaseModel):
    id: UUID
    title: str
    parent_id: UUID | None = None
    depth: int = 0
    position: int = 0
    status: str
    confidence: int | None = None
    mastery: int | None = None
    target_min: int | None = None
    last_studied_at: datetime | None = None
    next_review_at: datetime | None = None
    review_due: bool = False
    resource_total: int = 0
    resource_done: int = 0
    progress_pct: int = 0
    #: Alt agac (kendi + cocuklar) odak suresi -- pomodoro turevi.
    focus_minutes: int = 0
    focus_sessions: int = 0
    child_count: int = 0
    path: list[UUID] = Field(default_factory=list)
    resources: list[ResourceOut] | None = None


class StudyTreeTotals(BaseModel):
    topics: int = 0
    done: int = 0
    in_progress: int = 0
    review_due: int = 0
    resource_total: int = 0
    resource_done: int = 0
    focus_minutes: int = 0
    focus_sessions: int = 0


class StudyTreeOut(BaseModel):
    area: StudyAreaOut
    nodes: list[StudyTopicNode] = Field(default_factory=list)
    totals: StudyTreeTotals
    orphan_count: int = 0


class StudyTopicLegacyNode(BaseModel):
    """`GET /study/topics?area_id=` eski (ic ice) sekli -- yol korunur."""

    id: UUID
    title: str
    area_id: UUID
    parent_id: UUID | None = None
    status: str
    confidence: int | None = None
    target_min: int | None = None
    position: int = 0
    mastery: int | None = None
    last_studied_at: datetime | None = None
    interval_days: int = 0
    ease: float = 2.5
    review_count: int = 0
    last_reviewed_at: datetime | None = None
    next_review_at: datetime | None = None
    progress: TopicProgressOut = Field(default_factory=TopicProgressOut)
    children: list[StudyTopicLegacyNode] = Field(default_factory=list)


class TopicImpactOut(BaseModel):
    topics: int = 0
    resources: int = 0
    links: int = 0
    plan_slots: int = 0
    todos: int = 0


# ---------------------------------------------------------------------------
# Kaynaklar
# ---------------------------------------------------------------------------


class ResourceIn(BaseModel):
    title: str = Field(max_length=TITLE_MAX)
    url: str | None = Field(default=None, max_length=URL_MAX)
    kind: str = "link"
    position: int = 0
    note: str | None = Field(default=None, max_length=NOTE_MAX)
    estimated_min: int | None = Field(default=None, ge=1)

    _title = field_validator("title")(_clean_title)
    _url = field_validator("url")(_clean_url)

    @field_validator("kind")
    @classmethod
    def kind_known(cls, v: str) -> str:
        if v not in RESOURCE_KINDS:
            raise ValueError(f"kind su olmali: {RESOURCE_KINDS}")
        return v


class ResourcePatch(BaseModel):
    title: str | None = Field(default=None, max_length=TITLE_MAX)
    url: str | None = Field(default=None, max_length=URL_MAX)
    kind: str | None = None
    position: int | None = None
    note: str | None = Field(default=None, max_length=NOTE_MAX)
    estimated_min: int | None = Field(default=None, ge=1)
    #: true -> tamamlandi damgasi basilir, false -> kaldirilir.
    completed: bool | None = None

    _url = field_validator("url")(_clean_url)

    @field_validator("title")
    @classmethod
    def title_clean(cls, v: str | None) -> str | None:
        return _clean_title(v) if v is not None else None

    @field_validator("kind")
    @classmethod
    def kind_known(cls, v: str | None) -> str | None:
        if v is not None and v not in RESOURCE_KINDS:
            raise ValueError(f"kind su olmali: {RESOURCE_KINDS}")
        return v


class ResourceOut(BaseModel):
    id: UUID
    topic_id: UUID
    title: str
    url: str | None = None
    kind: str = "link"
    position: int = 0
    completed_at: datetime | None = None
    note: str | None = None
    estimated_min: int | None = None
    last_opened_at: datetime | None = None
    source: str = "manual"
    bookmark_id: UUID | None = None
    course_id: UUID | None = None


class AttachBookmarkIn(BaseModel):
    topic_id: UUID
    bookmark_id: UUID


# ---------------------------------------------------------------------------
# Tekrar (SRS)
# ---------------------------------------------------------------------------

#: Tekrar dereceleri `review.GRADES` ile ayni kume; API sozlesmesi Literal ile
#: daraltilir (yanlis derece 422 doner).


class TopicReviewIn(BaseModel):
    grade: Literal["forgot", "hard", "medium", "easy", "very_easy"]
    mastery: int | None = Field(default=None, ge=0, le=100)


class TopicReviewOut(ReviewBlockOut):
    pass


class ReviewTopicOut(BaseModel):
    id: UUID
    title: str
    area_id: UUID
    area_title: str
    status: str
    next_review_at: datetime | None = None
    mastery: int | None = None
    interval_days: int = 0
    review_count: int = 0
    last_reviewed_at: datetime | None = None
    confidence: int | None = None
    last_studied_at: datetime | None = None


class ReviewQueueOut(BaseModel):
    due_today: list[ReviewTopicOut] = Field(default_factory=list)
    overdue: list[ReviewTopicOut] = Field(default_factory=list)
    upcoming: list[ReviewTopicOut] = Field(default_factory=list)
    new_topics: list[ReviewTopicOut] = Field(default_factory=list)
    weak: list[ReviewTopicOut] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Istatistik / stale
# ---------------------------------------------------------------------------


class StatsAreaOut(BaseModel):
    area_id: UUID
    title: str
    minutes: int = 0


class StatsTopicOut(BaseModel):
    topic_id: UUID
    title: str
    minutes: int = 0


class StatsCourseOut(BaseModel):
    total: int = 0
    done: int = 0
    in_progress: int = 0


class StudyStatsOut(BaseModel):
    focus_minutes: int = 0
    focus_sessions: int = 0
    topics_done: int = 0
    topics_started: int = 0
    resources_done: int = 0
    reviews_done: int = 0
    active_days: int = 0
    streak_days: int = 0
    by_area: list[StatsAreaOut] = Field(default_factory=list)
    by_topic: list[StatsTopicOut] = Field(default_factory=list)
    planned_minutes: int = 0
    actual_minutes: int = 0
    courses: StatsCourseOut = Field(default_factory=StatsCourseOut)
    flashcards_reviewed: int = 0
    confidence_delta: int = 0


class StalePageOut(BaseModel):
    items: list[StudyTopicOut] = Field(default_factory=list)
    total: int = 0
    limit: int = 20
    offset: int = 0


# ---------------------------------------------------------------------------
# Degiskenlik
# ---------------------------------------------------------------------------


class TopicTodoIn(BaseModel):
    """Konu gorevi icin ortak alan sozlesmesi (Faz 31).

    Title/description konudan sabit kalir; plan_day/oncelik/tekrar/etiket
    gibi kullanici alanlari govdeden gelir -- "bugune al" tercihi plan_day
    olarak buradan uygulanir.
    """
    plan_day: date | None = None
    priority: int | None = Field(default=None, ge=0, le=3)
    due_at: datetime | None = None
    recur: str | None = None
    tags: list[str] = Field(default_factory=list)
    #: true -> acik gorev olsa bile yeni gorev uretir.
    force: bool = False


class TopicTodoOut(BaseModel):
    created: bool
    todo: TodoOut


# ---------------------------------------------------------------------------
# JSON ile konu agaci ice aktarma (Faz 36 / Faz 9)
# ---------------------------------------------------------------------------

#: Tek yuklemede izin verilen dugum/derinlik tavani -- elde uretilmis dev bir
#: dosya veritabanini doldurmasin.
MAX_IMPORT_NODES = 500
MAX_IMPORT_DEPTH = 6


class ResourceSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(max_length=TITLE_MAX)
    url: str | None = Field(default=None, max_length=URL_MAX)
    kind: str = "link"
    note: str | None = Field(default=None, max_length=NOTE_MAX)
    estimated_min: int | None = Field(default=None, ge=1)

    _title = field_validator("title")(_clean_title)
    _url = field_validator("url")(_clean_url)

    @field_validator("kind")
    @classmethod
    def kind_known(cls, v: str) -> str:
        if v not in RESOURCE_KINDS:
            raise ValueError(f"kind su olmali: {RESOURCE_KINDS}")
        return v


class TopicSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(max_length=TITLE_MAX)
    status: str = "not_started"
    target_min: int | None = Field(default=None, ge=1)
    #: Siralamada acik konum; verilmezse kardes sirasi kullanilir.
    position: int | None = Field(default=None, ge=0)
    resources: list[ResourceSeed] = Field(default_factory=list)
    children: list[TopicSeed] = Field(default_factory=list)

    _title = field_validator("title")(_clean_title)

    @field_validator("status")
    @classmethod
    def status_known(cls, v: str) -> str:
        if v not in TOPIC_STATUSES:
            raise ValueError(f"status su olmali: {TOPIC_STATUSES}")
        return v


class TopicImportIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    #: Var olan alana yukle. Yoksa `area` basligiyla yeni alan acilir.
    area_id: UUID | None = None
    area: str | None = Field(default=None, max_length=200)
    topics: list[TopicSeed] = Field(min_length=1)
    #: Eslesen konu/kaynak guncellensin mi (varsayilan: evet).
    update_existing: bool = True
    #: Agacta olmayan konulari ARSIVLE (silmez).
    prune: bool = False
    #: Ortak baslik onekini ("ilk90_ales - ") temizle.
    strip_common_prefix: bool = False

    @model_validator(mode="after")
    def area_given(self) -> TopicImportIn:
        if self.area_id is None and not (self.area or "").strip():
            raise ValueError("area_id ya da area verilmeli")
        total, depth = 0, 0

        def walk(nodes: list[TopicSeed], level: int) -> None:
            nonlocal total, depth
            depth = max(depth, level)
            for node in nodes:
                total += 1
                walk(node.children, level + 1)

        walk(self.topics, 1)
        if total > MAX_IMPORT_NODES:
            raise ValueError(f"en fazla {MAX_IMPORT_NODES} konu yuklenebilir (gelen: {total})")
        if depth > MAX_IMPORT_DEPTH:
            raise ValueError(f"en fazla {MAX_IMPORT_DEPTH} seviye ic ice olabilir")
        return self


class ImportAreaOut(BaseModel):
    id: UUID | None = None
    title: str
    exists: bool = False


class ImportNodePreview(BaseModel):
    path: str
    title: str
    status: str = "not_started"
    resources: int = 0
    changes: list[str] = Field(default_factory=list)


class ImportConflictOut(BaseModel):
    path: str
    reason: str


class ImportTotalsOut(BaseModel):
    nodes: int = 0
    depth: int = 0
    creates: int = 0
    updates: int = 0
    matches: int = 0


class ImportPreviewOut(BaseModel):
    area: ImportAreaOut
    creates: list[ImportNodePreview] = Field(default_factory=list)
    updates: list[ImportNodePreview] = Field(default_factory=list)
    matches: list[ImportNodePreview] = Field(default_factory=list)
    resources_new: int = 0
    resources_duplicate: int = 0
    conflicts: list[ImportConflictOut] = Field(default_factory=list)
    invalid: list[ImportConflictOut] = Field(default_factory=list)
    suggested_prefix: str | None = None
    totals: ImportTotalsOut


class TopicImportOut(BaseModel):
    area_id: UUID
    area_title: str
    topics_created: int
    topics_matched: int
    topics_updated: int = 0
    resources_created: int
    resources_skipped: int
    resources_updated: int = 0
    topics_archived: int = 0
    resources_archived: int = 0
