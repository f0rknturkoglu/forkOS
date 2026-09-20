"""H3 kanıt (Evidence) sözleşmeleri.

H3'ün tek ürünü bir `EvidenceBundle`'dır: "forkOS ne biliyor, bu bilgi nereden
geldi, ilgili kaynaklara nasıl ulaşıldı ve hangi sınırlar devreye girdi"
sorusunun **incelenebilir** cevabı.

Sınırlar bu modülde tek yerde tanımlanır; MCP şeması, çalışma zamanı denetimi
ve dokümantasyon AYNI sayıları gösterir (H2.2 dersi: belgelenen ama uygulanmayan
sınır, sınır değildir).

Bu modül KASITLI olarak şunları İÇERMEZ:

- `confidence`, `probability`, `truth_score`, `certainty`: forkOS'un kalibre
  edilmiş bir epistemik modeli YOKTUR; sahte kesinlik üretilmez (§31).
- `answer`, `summary_answer`, `conclusion`, `recommendation`: H3 yanıt üretmez,
  kanıt getirir (§5/§188).
- `hot_memory`, `conversation`, `model`, `inference` kaynak tipleri: sıcak
  hafıza kişiselleştirme bağlamıdır, kanıt değildir (§25/§26).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Girdi sınırları (§15/§114-§116)
# ---------------------------------------------------------------------------

MIN_QUERY_LENGTH = 2
MAX_QUERY_LENGTH = 200

MIN_EVIDENCE_LIMIT = 1
MAX_EVIDENCE_LIMIT = 15
DEFAULT_EVIDENCE_LIMIT = 12

MIN_EVIDENCE_DEPTH = 0
MAX_EVIDENCE_DEPTH = 2
DEFAULT_EVIDENCE_DEPTH = 1

# ---------------------------------------------------------------------------
# Çıktı bütçeleri (§35/§36/§38-§41/§149/§151)
# ---------------------------------------------------------------------------

#: Tek kanıt öğesinin snippet üst sınırı.
MAX_EVIDENCE_EXCERPT_CHARS = 1200
#: Global bütçeden kalan pay bu değerin altındaysa öğe eklenmez (§149).
MIN_USEFUL_EXCERPT_CHARS = 120
#: Tek bir yanıtta dönebilecek toplam snippet karakteri.
MAX_TOTAL_EVIDENCE_CHARS = 8000

#: Grafik gezinmesinde ziyaret edilebilecek en fazla düğüm (§38).
MAX_GRAPH_NODES = 25
#: Çapalı not genişletmesinde dikkate alınacak en fazla kasa notu (§39).
MAX_VAULT_NOTES_CONSIDERED = 12
#: Tek bir pakette dönebilecek en fazla olay kanıtı (§40).
MAX_EVENT_EVIDENCE = 8
#: Sorgu-only modda dönebilecek en fazla entity adayı (§41).
MAX_ENTITY_CANDIDATES = 5
#: Paket başına en fazla uyarı ve uyarı başına karakter (§151).
MAX_WARNINGS = 10
MAX_WARNING_CHARS = 300
#: Bir kanıt öğesinin seçilme gerekçesi için üst sınır (§106).
MAX_RETRIEVAL_REASON_CHARS = 240

#: Grafik gezinmesinde bir düğümün komşularını çekmek için tek sorguda
#: kabul edilen satır sayısı. Düğüm tavanı zaten işi sınırlar; bu ikinci
#: emniyet kemeridir (yoğun grafikte tek düğüm tüm bütçeyi yiyemez).
MAX_LINK_ROWS_PER_NODE = 200
#: Olay sorgusunda sıralama öncesi çekilen ham satır tavanı (§61).
MAX_EVENT_SCAN_ROWS = 120
#: Belirsiz bir wikilink için uyarıya eklenecek en fazla örnek yol (§93).
#: (Kasa tarama sınırları `obsidian/evidence.py` içindedir: dosya sistemi
#: davranışı kendi katmanında yaşar.)
MAX_AMBIGUOUS_LINK_SAMPLES = 5

# ---------------------------------------------------------------------------
# Numaralandırmalar
# ---------------------------------------------------------------------------

EvidenceScope = Literal["all", "operational", "knowledge"]

#: Kanıt KAYNAK tipleri (§25). Sıcak hafıza, konuşma, model çıkarımı YOKTUR.
EvidenceSourceType = Literal["entity", "event", "vault"]

#: Kanıtın çekirdeğe nasıl bağlandığı (§29).
EvidencePathKind = Literal["entity_link", "knowledge_pointer", "wikilink", "backlink"]

#: Getirme hattının aşamaları (§44).
RetrievalStage = Literal[
    "entity_resolution",
    "graph",
    "events",
    "managed_knowledge",
    "wikilinks",
    "backlinks",
    "vault_lexical",
    "budget",
]

#: Bir entity'nin pakete nasıl girdiği (§43). Lexical aday "çözülmüş gerçek"
#: gibi sunulmaz.
EntityResolutionKind = Literal["explicit_seed", "lexical_candidate"]

#: Paketin hangi sahiplik alanlarına dokunduğu (§42).
EvidenceSourceDomain = Literal["forkos", "f0rknbrain"]


# ---------------------------------------------------------------------------
# Modeller
# ---------------------------------------------------------------------------


class EvidenceLocator(BaseModel):
    """Kanıtın kaynaktaki yeri: hangi kayıt, hangi dosya, hangi satırlar.

    Anlamsız alanlar DOLDURULMAZ (§27); bilinmeyen değer `None` kalır. Satır
    numaraları yalnızca gerçek Markdown kaynağından türetilebiliyorsa verilir
    ve **1 tabanlıdır** (§28) -- yaklaşık değer UYDURULMAZ.
    """

    entity_id: str | None = Field(default=None, description="Operational entity UUID when the evidence is an entity.")
    event_id: int | None = Field(default=None, description="Append-only event sequence ID when the evidence is an event.")
    forkos_id: str | None = Field(default=None, description="Managed Vault note identity (stable across file moves).")
    relative_path: str | None = Field(default=None, description="Vault-relative path (provenance, not identity).")
    heading: str | None = Field(default=None, description="Containing Markdown heading, when one applies.")
    line_start: int | None = Field(default=None, description="1-based first source line of the excerpt, when provable.")
    line_end: int | None = Field(default=None, description="1-based last source line of the excerpt, when provable.")


class EvidencePathHop(BaseModel):
    """Çekirdekten kanıta giden tek bir adım (§29).

    `relation` DAİMA kanonik makine ilişkisidir (ör. `belongs_to`), yerelleşmiş
    etiket değil (§57).
    """

    kind: EvidencePathKind = Field(..., description="Hop kind: entity_link, knowledge_pointer, wikilink or backlink.")
    from_ref: str = Field(..., description="Source reference, e.g. 'entity:<uuid>' or 'vault:<relative_path>'.")
    relation: str = Field(..., description="Canonical machine relation, e.g. 'belongs_to' or 'knowledge_note'.")
    to_ref: str = Field(..., description="Target reference, e.g. 'entity:<uuid>' or 'vault:<relative_path>'.")


class EvidenceItem(BaseModel):
    """Tek bir incelenebilir kaynak parçası (§30).

    Kural: bir öğe = bir kaynak. İki kaynaktan gelen metin BİRLEŞTİRİLİP tek
    öğe gibi sunulmaz (§157).
    """

    evidence_id: str = Field(..., description="Deterministic ID: 'entity:<uuid>', 'event:<id>' or 'vault:<locator>#<heading>'.")
    source_type: EvidenceSourceType = Field(..., description="entity, event or vault. Hot memory is never a source.")
    source_id: str = Field(..., description="forkos_id for managed notes, relative_path otherwise; entity UUID; event ID.")
    title: str = Field(..., description="Human-readable title of the source.")
    locator: EvidenceLocator = Field(default_factory=EvidenceLocator, description="Where in the source this excerpt lives.")
    excerpt: str = Field(..., description="Bounded, deterministic excerpt of the source.")
    occurred_at: str | None = Field(default=None, description="Event time (ISO-8601) when the source is an event.")
    updated_at: str | None = Field(default=None, description="Canonical update time when the source exposes one.")
    relation_path: list[EvidencePathHop] = Field(default_factory=list, description="How this evidence connects to the explicit seed.")
    retrieval_reason: str = Field(..., description="Why this item was selected (bounded, <=240 chars). Not model reasoning.")
    truncated: bool = Field(default=False, description="True if the excerpt was shortened to fit a budget.")


class ResolvedEntityRef(BaseModel):
    """Pakete giren entity ve nasıl girdiği (§43)."""

    id: str = Field(..., description="Entity UUID.")
    type: str = Field(..., description="Entity type.")
    title: str = Field(..., description="Entity title.")
    route: str = Field(..., description="Web UI deep link route.")
    resolution: EntityResolutionKind = Field(..., description="explicit_seed or lexical_candidate.")
    expanded: bool = Field(..., description="True only when the graph was actually traversed from this entity.")


class RetrievalTraceStep(BaseModel):
    """Getirme hattının bir aşaması (§44/§45).

    Bu, modelin düşünme zinciri DEĞİLDİR: yalnızca sistemin hangi kanalı
    taradığını ve kaç aday kabul ettiğini söyler. Gizli akıl yürütme buraya
    YAZILMAZ.
    """

    stage: RetrievalStage = Field(..., description="Pipeline stage name.")
    description: str = Field(..., description="Factual description of what the stage did.")
    considered: int = Field(default=0, description="Candidates considered in this stage.")
    accepted: int = Field(default=0, description="Candidates accepted into the bundle from this stage.")
    truncated: bool = Field(default=False, description="True if this stage hit a hard cap.")


class EvidenceBundle(BaseModel):
    """H3'ün tek çıktısı (§42).

    Paket bir bağlam dökümü DEĞİLDİR (§105): yalnızca çekirdeğin doğrudan
    kanıtı ya da sorguyla ilgili olduğu gösterilebilen öğeler girer.
    """

    query: str = Field(..., description="The question or claim the evidence was retrieved for.")
    entity_seed: str | None = Field(default=None, description="Explicit entity UUID used as the retrieval root, if any.")
    resolved_entities: list[ResolvedEntityRef] = Field(default_factory=list, description="Entities that entered the bundle.")
    evidence: list[EvidenceItem] = Field(default_factory=list, description="Evidence items in deterministic priority order.")
    retrieval_trace: list[RetrievalTraceStep] = Field(default_factory=list, description="Factual record of the channels that ran.")
    sources_used: list[EvidenceSourceDomain] = Field(default_factory=list, description="Ownership domains actually consulted.")
    truncated: bool = Field(default=False, description="True if any retrieval channel or item was cut by a budget.")
    omitted_total: int = Field(default=0, description="Known (not estimated) candidates dropped by budgets.")
    warnings: list[str] = Field(default_factory=list, description="Bounded, model-readable warnings.")
    recovery_hint: str | None = Field(default=None, description="Actionable next step when the request can be improved.")
