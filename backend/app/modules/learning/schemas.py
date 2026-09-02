from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CourseIn(BaseModel):
    title: str = Field(min_length=1)
    platform: str | None = None
    url: str | None = None
    status: str = "planned"
    progress_pct: int = Field(0, ge=0, le=100)
    notes: str | None = None


class CoursePatch(BaseModel):
    title: str | None = None
    status: str | None = None
    progress_pct: int | None = Field(None, ge=0, le=100)
    notes: str | None = None


class AreaIn(BaseModel):
    title: str = Field(min_length=1)
    color: str | None = None
    position: int = 0





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
    tags: list[str] = []

class TopicIn(BaseModel):
    title: str = Field(min_length=1)
    area_id: UUID
    parent_id: UUID | None = None
    status: str = "not_started"
    confidence: int | None = Field(None, ge=1, le=5)
    target_min: int | None = Field(None, ge=1)
    position: int = 0


class TopicPatch(BaseModel):
    title: str | None = None
    parent_id: UUID | None = None
    status: str | None = None
    confidence: int | None = Field(None, ge=1, le=5)
    target_min: int | None = Field(None, ge=1)
    position: int | None = None


#: Kaynak turleri -- arayuz ikonu/rozeti bunlardan gelir.
RESOURCE_KINDS = ["link", "video", "article", "course", "book", "doc", "exercise"]


class ResourceIn(BaseModel):
    title: str = Field(min_length=1)
    url: str | None = None
    kind: str = "link"
    position: int = 0
    note: str | None = None

    @field_validator("kind")
    @classmethod
    def kind_known(cls, v: str) -> str:
        if v not in RESOURCE_KINDS:
            raise ValueError(f"kind su olmali: {RESOURCE_KINDS}")
        return v


class ResourcePatch(BaseModel):
    title: str | None = None
    url: str | None = None
    kind: str | None = None
    position: int | None = None
    note: str | None = None
    #: true -> tamamlandi damgasi basilir, false -> kaldirilir.
    completed: bool | None = None

    @field_validator("kind")
    @classmethod
    def kind_known(cls, v: str | None) -> str | None:
        if v is not None and v not in RESOURCE_KINDS:
            raise ValueError(f"kind su olmali: {RESOURCE_KINDS}")
        return v


# ---------------------------------------------------------------------------
# JSON ile konu agaci ice aktarma (Faz 36).
#
# Disarida (ornegin bir LLM'e yazdirarak) uretilen agac buradan yuklenir.
# Sozlesme BILEREK dar: baslik + kaynaklar + cocuklar. Bilinmeyen alanlar
# reddedilir ki elde uretilmis JSON sessizce yanlis yerlesmesin.
# ---------------------------------------------------------------------------

#: Tek yuklemede izin verilen dugum/derinlik tavani -- elde uretilmis dev bir
#: dosya veritabanini doldurmasin.
MAX_IMPORT_NODES = 500
MAX_IMPORT_DEPTH = 6

#: Konu durumlari -- uygulamanin TEK kumesi. Arayuz de bunu gosterir;
#: `patch_topic` "done"a gecisi tamamlanma olayi olarak yazar.
TOPIC_STATUSES = ["not_started", "in_progress", "done"]


class ResourceSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=300)
    url: str | None = Field(default=None, max_length=2000)
    kind: str = "link"
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("kind")
    @classmethod
    def kind_known(cls, v: str) -> str:
        if v not in RESOURCE_KINDS:
            raise ValueError(f"kind su olmali: {RESOURCE_KINDS}")
        return v


class TopicSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=300)
    status: str = "not_started"
    target_min: int | None = Field(default=None, ge=1)
    resources: list[ResourceSeed] = Field(default_factory=list)
    children: list["TopicSeed"] = Field(default_factory=list)

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
    area: str | None = Field(default=None, min_length=1, max_length=200)
    topics: list[TopicSeed] = Field(min_length=1)

    @model_validator(mode="after")
    def area_given(self) -> "TopicImportIn":
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


class TopicImportOut(BaseModel):
    area_id: UUID
    area_title: str
    topics_created: int
    topics_matched: int
    resources_created: int
    resources_skipped: int
