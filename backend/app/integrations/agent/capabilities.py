"""H0–H7 ve A5 Brain Interface yetenek metadatası — TEK kaynak.

Bu dosya MCP yüzeyinin aile haritasını ve sunucu talimatını tutar; hem MCP
sunucusu (`mcp.py`) hem Ayarlar teşhis ucu (`/api/agent/status`) buradan okur.
`tools.py` içindeki GERÇEK kayıt sırası ile buradaki liste birbirinden
kopamaz: tutarlılık `tests/test_agent_capabilities.py` içinde
`mcp_server.list_tools()` ile iki yönlü karşılaştırılarak ZORLANIR (araç adı
kümesi eşitliği + aile başına sayılar + yinelenen ad yasağı).

Kural: yeni bir araç eklerken/aile değiştirirken ÖNCE burası güncellenir,
sonra `tools.py` kaydı ve testler yeşile getirilir. Aileler tarihsel Hermes
fazlarıdır (H0–H7, A5) ve araç adları sunucudaki gerçek adlarla birebir aynıdır.
"""

from __future__ import annotations

from dataclasses import dataclass

#: MCP sunucu kimliği. `mcp.py` ve teşhis yükü aynı değeri gösterir.
SERVER_NAME = "forkos-brain"

#: Taşıma biçimi (MCP Streamable HTTP). stdio YOKTUR: arayüz loopback HTTP'dir.
TRANSPORT = "streamable_http"

#: Arayüzün HTTP yolu. `main.py` bu yolu `streamable_http_path="/"` ile mount eder.
MCP_PATH = "/mcp"

#: Arayüz yalnızca loopback'e bağlanır; uzak istemci yüzeyi YOKTUR.
LOOPBACK_ONLY = True


@dataclass(frozen=True)
class FamilySpec:
    """Bir Hermes fazının dışa vurulan yetenek özeti.

    `tools` sunucudaki GERÇEK araç adlarıdır; sıra kayıt sırasıyla aynıdır.
    """

    id: str
    label: str
    summary: str
    tools: tuple[str, ...]


#: Aileler H0..H7 ve A5 sırasındadır. Sıra sözleşmedir: teşhis yükü ve talimat metni
#: bu sırayı korur, testler sırayı da doğrular.
FAMILIES: tuple[FamilySpec, ...] = (
    FamilySpec(
        id="H0",
        label="Operasyonel bağlam",
        summary="Gün brifingi, operasyonel arama, varlık/proje bağlamı, son hareketler ve kasa okuma.",
        tools=(
            "forkos_briefing",
            "forkos_search",
            "forkos_entity_context",
            "forkos_project_context",
            "forkos_recent_activity",
            "brain_status",
            "brain_search",
            "brain_read",
        ),
    ),
    FamilySpec(
        id="H1",
        label="Güvenli yazma",
        summary="Tek kapsamlı, onaylı mutasyonlar: todo, proje next_action, ilan/başvuru geçişi, bookmark ve kasa yakalama.",
        tools=(
            "forkos_todo_create",
            "forkos_todo_update",
            "forkos_todo_complete",
            "forkos_todo_plan",
            "forkos_project_update",
            "forkos_opportunity_transition",
            "forkos_application_transition",
            "forkos_bookmark_capture",
            "forkos_bookmark_update",
            "brain_capture",
            "brain_save_to_entity",
        ),
    ),
    FamilySpec(
        id="H2",
        label="Sıcak bellek",
        summary="Profil, tercih, hedef ve kararların kürasyonlu kalıcı belleği; emeklilik silme değildir.",
        tools=(
            "hot_memory_context",
            "hot_memory_list",
            "hot_memory_store",
            "hot_memory_update",
            "hot_memory_retire",
        ),
    ),
    FamilySpec(
        id="H3",
        label="Kanıt",
        summary="Bir soru veya iddia için incelenebilir kanıt getirir; güven puanı üretmez.",
        tools=("forkos_evidence",),
    ),
    FamilySpec(
        id="H4",
        label="Yerel biliş",
        summary="Yalnızca loopback modeliyle tek yerel biliş ilkeli (sınıflama, yapılandırılmış çıkarım, sorgu yeniden yazımı).",
        tools=("forkos_local_cognition",),
    ),
    FamilySpec(
        id="H5",
        label="İnceleme zekâsı",
        summary="Mevcut durum üzerine sınırlı düşünme: süreklilik, dönem farkı, günlük kapanış, haftalık inceleme ve anlamsal hafıza adayları.",
        tools=(
            "forkos_review_intelligence",
            "semantic_memory_candidates",
            "semantic_memory_promote",
        ),
    ),
    FamilySpec(
        id="H6",
        label="Proaktivite",
        summary="forkOS'un ne zaman sana geleceğini yönetir: dikkat katmanı, otomasyon motoru değil.",
        tools=("forkos_proactivity",),
    ),
    FamilySpec(
        id="H7",
        label="Kalıcı yürütme",
        summary="Kanıttan plan önerir; yalnızca kullanıcının onayladığı revizyonu H1 yazma araçlarıyla yürütür.",
        tools=("forkos_execution",),
    ),
    FamilySpec(
        id="A5",
        label="Yerel yargı",
        summary="H3 kanıtını, A4 hafıza adayını ve açık iddiaları yerel, salt-okunur biçimde değerlendirir; yazma yetkisi vermez.",
        tools=("forkos_context_judge", "forkos_memory_judge", "forkos_answer_judge"),
    ),
    FamilySpec(
        id="Career",
        label="Kariyer zekâsı",
        summary="Yerel görüşme hazırlığı, sınırlı prova, kullanıcı debrief'i ve salt-okunur sonuç analitiği.",
        tools=("forkos_career_interview", "forkos_career_insights"),
    ),
)

#: Talimat metninde her ailenin ROLÜ. `FAMILIES` ile birebir örtüşmek zorundadır:
#: eksik bir aile `instructions()` çağrısını sessizce atlamaz, KeyError verir.
_FAMILY_ROLE: dict[str, str] = {
    "Career": "Career: evidence-bound interview artifacts require approval for writes; insights are deterministic associations without mutations, never employer motives or automatic actions.",
    "H0": (
        "H0 operational and knowledge context: day briefing, operational search, "
        "entity/project context, recent activity, and Vault knowledge status, search and read."
    ),
    "H1": (
        "H1 safe writes: single, explicitly scoped mutations (todos, project next_action, "
        "opportunity/application transitions, bookmarks, Vault capture) that require user "
        "approval when this server is configured as untrusted."
    ),
    "H2": (
        "H2 hot memory: the small curated set of durable profile, preference, goal, constraint "
        "and decision items; retiring an item stops its use without deleting history."
    ),
    "H3": (
        "H3 evidence: inspectable evidence for a question or claim, drawn from operational state "
        "and the Vault, without confidence scores or generated answers."
    ),
    "H4": (
        "H4 local cognition: one explicitly chosen primitive executed by the configured local "
        "model over loopback only, with no external network call."
    ),
    "H5": (
        "H5 review intelligence: bounded reflection over existing state (continuity, period "
        "delta, daily close, weekly review, consolidation candidates) and controlled semantic memory promotion."
    ),
    "H6": (
        "H6 proactivity: inspect and control when forkOS proactively surfaces things; this is the "
        "attention layer, not an automation engine."
    ),
    "H7": (
        "H7 durable execution: propose an action plan from evidence, let the user approve one "
        "exact revision, then execute strictly through the H1 write tools."
    ),
    "A5": (
        "A5 local judgment: optional semantic prioritization of H3-eligible evidence, advisory "
        "judgments about A4 memory candidates, and answer evidence support judgment for explicit "
        "claims, with no canonical writes, answer rewrites, or delivery blocking authority."
    ),
}


def tool_count() -> int:
    """Kayıtlı toplam araç sayısı (aileler üzerinden)."""
    return sum(len(family.tools) for family in FAMILIES)


def family_counts() -> dict[str, int]:
    """Aile kimliği → araç sayısı. Sıra H0..H7'dir."""
    return {family.id: len(family.tools) for family in FAMILIES}


def family_tools(family_id: str) -> frozenset[str]:
    """Bir ailenin araç adları. Bilinmeyen aile sessizce boş DÖNMEZ."""
    for family in FAMILIES:
        if family.id == family_id:
            return frozenset(family.tools)
    raise KeyError(f"unknown capability family: {family_id}")


def all_tools() -> frozenset[str]:
    """Tüm ailelerin araç adları. Yinelenen ad varsa bu bir sözleşme ihlalidir."""
    names = [name for family in FAMILIES for name in family.tools]
    if len(names) != len(set(names)):
        duplicates = sorted({name for name in names if names.count(name) > 1})
        raise AssertionError(f"duplicate tool names in capabilities: {duplicates}")
    return frozenset(names)


def tool_to_family(tool_name: str) -> str:
    """Bir aracın aile kimliği. Bilinmeyen araç sessizce eşleşmez."""
    for family in FAMILIES:
        if tool_name in family.tools:
            return family.id
    raise KeyError(f"tool is not declared in capabilities: {tool_name}")


def instructions() -> str:
    """MCP sunucu talimatı — arayüzün GERÇEK kapsamını anlatır.

    Metin bilinçli olarak "salt okunur gözlemci" DEMEZ: yüzey hem okuma hem de
    onaylı yazma araçları içerir. Aile listesi `FAMILIES`'ten türetilir, bu
    yüzden yeni bir aile eklendiğinde talimat da onu anlatmak zorunda kalır.
    """
    parts = [
        "forkOS Brain Interface: a bounded operational and knowledge interface for a "
        "local-first personal workspace. The interface is exposed over loopback HTTP only "
        "and never calls an external network; the only network traffic is the configured "
        "local model provider, and only when local cognition is enabled.",
    ]
    for family in FAMILIES:
        parts.append(_FAMILY_ROLE[family.id])
    parts.append(
        "Prefer the narrowest tool that answers the request, treat tool results as bounded "
        "evidence rather than certainty, and never claim that a write happened unless the tool "
        "returned a receipt."
    )
    return " ".join(parts)


__all__ = [
    "FAMILIES",
    "LOOPBACK_ONLY",
    "MCP_PATH",
    "SERVER_NAME",
    "TRANSPORT",
    "FamilySpec",
    "all_tools",
    "family_counts",
    "family_tools",
    "instructions",
    "tool_count",
    "tool_to_family",
]
