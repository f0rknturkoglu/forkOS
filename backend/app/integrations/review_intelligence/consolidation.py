"""H5 konsolidasyon — geçici malzemeden kalıcılık ADAYLARI (§51/§114).

Zincir:

```text
günlük notlar + Event'ler        (episodic)
      ↓  sınırlı kaynak paketi
H4 structured_extract            (consolidation_candidates_v1)
      ↓  kaynak eşlemesi (birebir alıntı → kaynak ref)
PromotionCandidate[]             (aday; doğruluk DEĞİL)
      ↓  (isteğe bağlı) H3 kanıtı + H4 classify
KnowledgeHealthCandidate[]       (olası eskime/yerine geçme)
```

Değişmezler: H5 hiçbir şey yazmaz; H4 çıktısı doğruluk değildir; Hot Memory
tarihsel kanıt değildir; özet kanıt değildir.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.local_cognition import models as lc_models
from app.integrations.local_cognition import service as lc_svc
from app.integrations.review_intelligence import policy as policy_svc
from app.integrations.review_intelligence import sources as source_svc
from app.integrations.review_intelligence.models import (
    MAX_H5_H3_ITEMS_PER_CANDIDATE,
    MAX_H5_H4_FRAGMENTS,
    MAX_H5_H4_PACKET_CHARS,
    MAX_H5_KNOWLEDGE_HEALTH,
    MAX_H5_RESURFACE,
    MAX_H5_SUPERSESSION_CHECKS,
    RESURFACE_AGE_DAYS,
    Collector,
    KnowledgeHealthCandidate,
    PossibleOpenLoop,
    PromotionCandidate,
    ResurfaceCandidate,
    SourceRef,
)

#: Kaynak paketinde kullanılan sınırlayıcılar (§57).
SOURCE_OPEN = "<<<SOURCE {marker}>>>"
SOURCE_CLOSE = "<<<END {marker}>>>"

#: H4 classify etiketleri (§76) — serbest metin DEĞİL.
SUPERSESSION_LABELS: tuple[str, ...] = (
    "consistent",
    "possibly_superseded",
    "possibly_conflicting",
    "unrelated",
)

SUPERSESSION_GOAL = (
    "Compare the OLD stored knowledge with the NEW candidate. "
    "Choose 'possibly_superseded' only if the new statement replaces the old one, "
    "'possibly_conflicting' if they contradict, 'consistent' if both can hold, "
    "'unrelated' if they are about different things."
)


def build_packet(fragments: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]], bool]:
    """Sınırlı H4 kaynak paketini kurar (§56).

    Döner: `(packet_text, used_fragments, truncated)`. Parça sayısı ve toplam
    karakter tavanı aşılırsa `truncated=True` olur; sessiz kırpma yoktur.
    """
    used: list[dict[str, Any]] = []
    parts: list[str] = []
    total = 0
    truncated = False

    for index, fragment in enumerate(fragments):
        if len(used) >= MAX_H5_H4_FRAGMENTS:
            truncated = True
            break
        text = (fragment.get("text") or "").strip()
        if not text:
            continue
        marker = f"source_{index + 1}"
        block = f"{SOURCE_OPEN.format(marker=marker)}\n{text}\n{SOURCE_CLOSE.format(marker=marker)}"
        if total + len(block) > MAX_H5_H4_PACKET_CHARS:
            truncated = True
            break
        parts.append(block)
        total += len(block)
        used.append({**fragment, "marker": marker, "text": text})

    return "\n\n".join(parts), used, truncated


def _map_excerpt_to_source(
    excerpt: str, used_fragments: list[dict[str, Any]]
) -> tuple[dict[str, Any] | None, bool]:
    """Birebir alıntıyı kaynağa geri eşler (§57).

    Birden fazla parçada geçiyorsa tahmin EDİLMEZ: `(None, ambiguous=True)`.
    """
    from app.integrations.local_cognition.contracts import excerpt_is_sourced

    matches = [
        fragment for fragment in used_fragments if excerpt_is_sourced(excerpt, fragment["text"])
    ]
    if len(matches) == 1:
        return matches[0], False
    if len(matches) > 1:
        return None, True
    return None, False


async def extract_promotion_candidates(
    session: AsyncSession,
    collector: Collector,
    *,
    fragments: list[dict[str, Any]],
    focus_entity_id: uuid.UUID | None,
) -> list[PromotionCandidate]:
    """H4 ile sınırlı aday çıkarımı; H4 yoksa boş liste + uyarı (§79)."""
    if not fragments:
        collector.step("h4_candidates_extracted", considered=0, accepted=0)
        return []

    packet, used, packet_truncated = build_packet(fragments)
    collector.manifest.truncated = collector.manifest.truncated or packet_truncated
    if packet_truncated:
        collector.warn("SOURCE_PACKET_TRUNCATED", f"{len(fragments)} parçanın sınırlı kısmı kullanıldı")
    if not packet:
        collector.step("h4_candidates_extracted", considered=0, accepted=0)
        return []

    request = lc_models.StructuredExtractRequest(
        lane="structured_extract", text=packet, contract="consolidation_candidates_v1"
    )

    raw_candidates: list[dict[str, Any]] = []
    calls = 0
    try:
        response = await lc_svc.run_local_cognition(request)
        calls += 1
        if response.status != "success" or response.result is None:
            collector.warn("H4_UNAVAILABLE", response.failure_code or "candidate extraction failed")
            collector.step("h4_candidates_extracted", considered=0, accepted=0, truncated=False)
            return []
        raw_candidates = list(response.result.items)
        collector.manifest.h4_used = True
    except lc_models.H4Error as exc:
        collector.warn("H4_UNAVAILABLE", exc.code)
        collector.step("h4_candidates_extracted", considered=0, accepted=0)
        return []
    except Exception:  # noqa: BLE001 - H5 asla H4 yüzünden düşmez
        collector.warn("H4_UNAVAILABLE", "local cognition unavailable")
        collector.step("h4_candidates_extracted", considered=0, accepted=0)
        return []

    collector.manifest.h4_used = collector.manifest.h4_used or calls > 0

    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for item in raw_candidates[: lc_models.MAX_EXTRACTION_ITEMS]:
        kind = str(item.get("kind") or "")
        text = str(item.get("text") or "").strip()
        excerpt = str(item.get("source_excerpt") or "")
        if not kind or not text:
            continue
        fragment, ambiguous = _map_excerpt_to_source(excerpt, used)
        if ambiguous:
            collector.warn("AMBIGUOUS_CANDIDATE_SOURCE", "alıntı birden fazla parçada geçiyor; atlandı")
            continue
        if fragment is None:
            continue

        ref = str(fragment.get("ref") or "")
        key = (kind, policy_svc.normalize_for_identity(text))
        entry = grouped.setdefault(
            key,
            {
                "kind": kind,
                "text": text,
                "support_refs": [],
                "excerpts": [],
                "entity_id": fragment.get("entity_id"),
            },
        )
        if ref and ref not in entry["support_refs"]:
            entry["support_refs"].append(ref)
        entry["excerpts"].append(excerpt)

    candidates: list[PromotionCandidate] = []
    memories = source_svc.active_hot_memories()
    memory_index = {
        policy_svc.normalize_for_identity(memory["text"]): memory["ref"] for memory in memories
    }
    collector.manifest.hot_memory_checked = len(memories)

    for entry in grouped.values():
        kind = entry["kind"]
        entity_scoped = bool(entry["entity_id"]) or bool(focus_entity_id)
        destination = policy_svc.destination_for(kind, entity_scoped=entity_scoped)  # type: ignore[arg-type]
        support_refs = sorted(entry["support_refs"])
        candidate = PromotionCandidate(
            candidate_id=policy_svc.candidate_id(kind, entry["text"], support_refs),
            kind=kind,  # type: ignore[arg-type]
            text=entry["text"],
            suggested_destination=destination,
            support_refs=support_refs,
            source_count=len(support_refs),
            recurrence_count=max(len(support_refs), 1),
        )
        # §81: yalnızca TAM (normalize) eşleşme "zaten var" sayılır.
        existing = memory_index.get(policy_svc.normalize_for_identity(entry["text"]))
        if existing and destination == "hot_memory":
            candidate.status = "already_present"
            candidate.warnings.append("HOT_MEMORY_EXACT_DUPLICATE")
        candidates.append(candidate)

    candidates.sort(key=policy_svc.promotion_sort_key)
    candidates = candidates[: lc_models.MAX_EXTRACTION_ITEMS]
    collector.step(
        "h4_candidates_extracted",
        considered=len(raw_candidates),
        accepted=len(candidates),
        truncated=packet_truncated,
    )
    return candidates


async def possible_open_loops(
    session: AsyncSession,
    collector: Collector,
    *,
    candidates: list[PromotionCandidate],
) -> list[PossibleOpenLoop]:
    """Taahhüt adayları için KONSERVATİF kanonik eşleşme (§65-§67)."""
    commitments = [item for item in candidates if item.kind == "commitment"]
    if not commitments:
        return []

    index = await source_svc.todo_title_index(session, limit=500)
    loops: list[PossibleOpenLoop] = []
    for candidate in commitments[: lc_models.MAX_EXTRACTION_ITEMS]:
        key = policy_svc.normalize_for_identity(candidate.text)
        todo_id = index.get(key)
        loops.append(
            PossibleOpenLoop(
                text=candidate.text,
                support_refs=list(candidate.support_refs),
                matching_todo_id=todo_id,
                match_state="exact_match" if todo_id else "no_exact_match",
            )
        )
    collector.step("budget_applied", considered=len(commitments), accepted=len(loops))
    return loops


def knowledge_scope(collector: Collector) -> bool:
    """Bilgi sinyali üretilebilir mi (§143)?

    Kasa yapılandırılmamış/erişilemiyorsa bilgi okuması YAPILMAZ ve durum
    açıkça raporlanır: sessiz boş liste, "bilgi yok" gibi okunurdu.
    """
    if source_svc.vault_root() is None:
        collector.warn("VAULT_UNAVAILABLE", "kasa kökü yapılandırılmamış veya erişilemiyor")
        return False
    return True


def report_index_conflicts(collector: Collector) -> None:
    """İndeks tarandıktan SONRA çağrılır: çelişen/bozuk yönetilen dosyalar (§159).

    Çelişkili kimlik yönetilen notu belirsiz kılar; bu, üretilen bilgi
    sinyallerinin kapsamını daraltır ve gizlenmemelidir.
    """
    from app.integrations.obsidian.service import vault_index

    conflicts = vault_index.get_conflict_count()
    invalid = len(vault_index.invalid_files)
    if conflicts or invalid:
        collector.warn(
            "CONFLICTING_KNOWLEDGE",
            f"{conflicts} çakışan kimlik, {invalid} geçersiz metadata",
        )


async def stale_managed_notes(
    session: AsyncSession,
    collector: Collector,
    *,
    entity_ids: list[uuid.UUID],
    now: Any,
) -> list[KnowledgeHealthCandidate]:
    """Operasyonel durum yönetilen nottan YENİYSE olası eskime (§73).

    Bu bir ÇELİŞKİ kanıtı değildir; yalnızca "gözden geçirmeye değer" der.
    """
    if not entity_ids:
        return []

    from app.core.models import Entity

    rows = (
        await session.execute(
            select(Entity.id, Entity.title, Entity.type, Entity.updated_at).where(
                Entity.id.in_(entity_ids)
            )
        )
    ).all()

    results: list[KnowledgeHealthCandidate] = []
    for entity_id, title, entity_type, updated_at in rows:
        if len(results) >= MAX_H5_KNOWLEDGE_HEALTH:
            collector.warn("KNOWLEDGE_HEALTH_TRUNCATED")
            collector.truncated = True
            break
        note = source_svc.managed_note_meta(entity_id)
        if note is None:
            continue
        if note.get("state") == "conflict":
            results.append(
                KnowledgeHealthCandidate(
                    issue="managed_source_conflict",
                    reason="managed_id_claimed_by_multiple_files",
                    text=f"'{title or entity_type}' için yönetilen not kimliği çakışıyor.",
                    support_refs=[f"entity:{entity_id}"],
                    source_count=1,
                    entity_id=str(entity_id),
                )
            )
            continue
        if note.get("mtime") is None:
            continue
        from datetime import datetime

        note_time = datetime.fromisoformat(str(note["mtime"]))
        if updated_at is not None and updated_at > note_time:
            ref = collector.add_source(
                SourceRef(
                    ref=f"vault:{note['relative_path']}",
                    domain="vault",
                    kind="managed_note",
                    title=note.get("title"),
                    timestamp=str(note["mtime"]),
                    entity_id=str(entity_id),
                    locator=str(note["relative_path"]),
                )
            )
            results.append(
                KnowledgeHealthCandidate(
                    issue="possibly_stale",
                    reason="operational_state_newer_than_managed_note",
                    text=(
                        f"'{title or entity_type}' kaydı yönetilen nottan sonra güncellendi; "
                        "not gözden geçirmeye değer olabilir."
                    ),
                    support_refs=[f"entity:{entity_id}", ref],
                    source_count=2,
                    entity_id=str(entity_id),
                )
            )
    collector.step("knowledge_health_checked", considered=len(rows), accepted=len(results))
    return results


async def supersession_candidates(
    session: AsyncSession,
    collector: Collector,
    *,
    candidates: list[PromotionCandidate],
    focus_entity_id: uuid.UUID | None,
) -> list[KnowledgeHealthCandidate]:
    """Sınırlı semantik yerine-geçme karşılaştırması (§76-§78).

    Yeni `decision`/`project_knowledge` adayı için güncel kanıt H3'ten ÇEKİLİR,
    sonra en fazla bir çift H4 `classify` ile karşılaştırılır. Sonuç yalnızca
    ADAYDIR; otomatik geçersiz kılma YOKTUR.
    """
    if focus_entity_id is None:
        return []

    targets = [
        item for item in candidates if item.kind in {"decision", "project_knowledge"}
    ][:MAX_H5_SUPERSESSION_CHECKS]
    if not targets:
        return []

    from app.integrations.agent import evidence as evidence_svc

    results: list[KnowledgeHealthCandidate] = []
    for candidate in targets:
        try:
            bundle = await evidence_svc.retrieve_evidence(
                session,
                query=candidate.text,
                entity_id=str(focus_entity_id),
                scope="knowledge",
                limit=MAX_H5_H3_ITEMS_PER_CANDIDATE,
            )
        except Exception:  # noqa: BLE001 - H3 yoksa aday üretilmez
            collector.warn("H3_EVIDENCE_UNAVAILABLE")
            return results

        vault_items = [
            item for item in bundle.evidence if item.source_type == "vault" and item.excerpt
        ][:MAX_H5_H3_ITEMS_PER_CANDIDATE]
        if not vault_items:
            continue

        refs = collector.add_evidence([item.model_dump(mode="json") for item in vault_items])
        collector.manifest.h3_evidence_ids.extend(
            item.evidence_id for item in vault_items
        )

        old_excerpt = vault_items[0].excerpt
        request = lc_models.ClassifyRequest(
            lane="classify",
            text=(
                "OLD stored knowledge:\n"
                f"{old_excerpt[:600]}\n\n"
                "NEW candidate statement:\n"
                f"{candidate.text[:600]}"
            ),
            labels=list(SUPERSESSION_LABELS),
            classification_goal=SUPERSESSION_GOAL,
        )
        try:
            response = await lc_svc.run_local_cognition(request)
        except lc_models.H4Error as exc:
            collector.warn("H4_UNAVAILABLE", exc.code)
            return results
        if response.status != "success" or response.result is None:
            collector.warn("H4_UNAVAILABLE", response.failure_code or "classification failed")
            return results
        collector.manifest.h4_used = True

        label = response.result.label
        if label in {"possibly_superseded", "possibly_conflicting"}:
            results.append(
                KnowledgeHealthCandidate(
                    issue=label,
                    reason=f"h4_classify:{label}",
                    text=candidate.text,
                    support_refs=[*candidate.support_refs, *refs],
                    source_count=len(candidate.support_refs) + len(refs),
                    entity_id=str(focus_entity_id),
                )
            )
        if len(results) >= MAX_H5_KNOWLEDGE_HEALTH:
            collector.warn("KNOWLEDGE_HEALTH_TRUNCATED")
            collector.truncated = True
            break

    collector.step("h3_evidence_loaded", considered=len(targets), accepted=len(results))
    return results


async def resurface_candidates(
    session: AsyncSession,
    collector: Collector,
    *,
    entity_ids: list[uuid.UUID],
    now: Any,
) -> list[ResurfaceCandidate]:
    """Yapısal olarak ilgili, eskimiş bilgi (§83/§84/§85).

    Rastgele "günün notu" DEĞİLDİR: yalnızca aktif entity'lere bağlı yönetilen
    notlar, belgelenmiş yaş eşiğini geçtiyse önerilir.
    """
    if not entity_ids:
        return []

    from app.core.models import Entity

    rows = (
        await session.execute(
            select(Entity.id, Entity.title).where(Entity.id.in_(entity_ids))
        )
    ).all()
    title_by_id = {str(entity_id): title for entity_id, title in rows}

    results: list[ResurfaceCandidate] = []
    for entity_id in entity_ids:
        if len(results) >= MAX_H5_RESURFACE:
            break
        note = source_svc.managed_note_meta(entity_id)
        if note is None or note.get("state") != "available" or note.get("age_days") is None:
            continue
        age_days = int(note["age_days"])
        if age_days < RESURFACE_AGE_DAYS:
            continue
        ref = collector.add_source(
            SourceRef(
                ref=f"vault:{note['relative_path']}",
                domain="vault",
                kind="managed_note",
                title=note.get("title"),
                timestamp=str(note.get("mtime")),
                entity_id=str(entity_id),
                locator=str(note["relative_path"]),
            )
        )
        results.append(
            ResurfaceCandidate(
                ref=ref,
                title=str(note.get("title") or title_by_id.get(str(entity_id)) or "Not"),
                age_days=age_days,
                related_entity_id=str(entity_id),
                reasons=[
                    "related_active_entity=true",
                    f"age_days={age_days}",
                    "source_still_available=true",
                ],
            )
        )

    results.sort(key=lambda item: (-item.age_days, item.ref))
    # İz adımı ÜRETİLMEZ: yeniden yüzeye çıkarma, aynı `knowledge_health_checked`
    # adımının parçasıdır; ikinci bir adım izi yanıltıcı biçimde çoğaltırdı.
    return results


__all__ = [
    "SUPERSESSION_GOAL",
    "SUPERSESSION_LABELS",
    "build_packet",
    "extract_promotion_candidates",
    "knowledge_scope",
    "report_index_conflicts",
    "possible_open_loops",
    "resurface_candidates",
    "stale_managed_notes",
    "supersession_candidates",
]
