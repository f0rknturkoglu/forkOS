"""H2 sıcak hafıza adaptörleri: sınırlı bağlam, liste ve onaylı mutasyonlar.

Katman sınırı:
  depolama (Vault dosya sistemi) → `integrations/obsidian/hot_memory.py`
  anlam/bağlam/sınırlar          → burası

Bu modül KARAR VERMEZ ("bu önemli görünüyor" gibi). Yalnızca deterministik iş
yapar: şema, sınır, kimlik, revizyon, yol güvenliği, kesin tekrar tespiti,
zaman aşımı ve durum. Anlamsal yargı Hermes'e aittir (§77).

Okuma yolları PostgreSQL'e BAĞIMLI DEĞİLDİR (§126): yalnızca ilgili kayıt
doğrulaması yapılan yazmalar oturum kullanır.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.links import FROZEN_LEGACY_ENTITY_TYPES
from app.core.models import Entity
from app.integrations.agent.actions import ActionError
from app.integrations.agent.hot_memory_models import (
    MAX_QUERY_LENGTH,
    EffectiveStatusFilter,
    HotMemoryContextData,
    HotMemoryItem,
    HotMemoryListData,
    HotMemoryListItem,
    HotMemoryRetireIn,
    HotMemoryStoreIn,
    HotMemoryUpdateIn,
    MemoryKindValue,
)
from app.integrations.agent.write_models import ActionReceipt
from app.integrations.obsidian import hot_memory as storage

#: §44 bağlam bütçesi: öğe sayısı ve metin karakteri üst sınırı.
CONTEXT_ITEM_CAP = 24
CONTEXT_CHAR_BUDGET = 6000

#: Tür başına üst sınır; global tavan yine kazanır.
KIND_CAPS: dict[str, int] = {
    "profile": 5,
    "preference": 6,
    "goal": 5,
    "constraint": 6,
    "decision": 6,
}

#: Bağlam paketinde kararlı kategori sırası (§46).
KIND_ORDER: tuple[str, ...] = ("profile", "preference", "goal", "constraint", "decision")

#: Kategori → bağlam alanı adı.
CONTEXT_FIELDS: dict[str, str] = {
    "profile": "profile",
    "preference": "preferences",
    "goal": "goals",
    "constraint": "constraints",
    "decision": "decisions",
}

LIST_DEFAULT_LIMIT = 20
LIST_MAX_LIMIT = 50

def _to_action_error(exc: storage.HotMemoryError) -> ActionError:
    """Depolama hatasını H1'in model-okunur hata zarfına çevirir (kod korunur)."""
    message = str(exc)
    _, _, detail = message.partition(": ")
    return ActionError(exc.code, detail or message)


def _storage_error(exc: Exception) -> ActionError:
    """Depolama hatasını model-okunur zarfa çevirir (§28/§85).

    Ham `OSError` de `HOT_MEMORY_UNAVAILABLE` olur: dosya sistemi istisnası,
    yığın izi ya da mutlak yol hiçbir koşulda ajana sızmaz.
    """
    if isinstance(exc, storage.HotMemoryError):
        return _to_action_error(exc)
    return ActionError("HOT_MEMORY_UNAVAILABLE", "hafıza deposuna erişilemedi")


def _read_root():
    root = storage.readable_root()
    if root is None:
        raise ActionError("HOT_MEMORY_UNAVAILABLE", "Obsidian Vault erişilebilir değil")
    return root


def _write_root():
    try:
        return storage.writable_root()
    except storage.HotMemoryError as exc:
        raise _to_action_error(exc) from exc


def _scan(root):
    """Depolama taraması; depolama hataları H1 hata zarfına çevrilir.

    Ham `OSError` da `HOT_MEMORY_UNAVAILABLE` olur: okuma yolları hiçbir koşulda
    dosya sistemi istisnası ya da mutlak yol sızdırmaz (§28).
    """
    try:
        return storage.scan_memories(root)
    except (storage.HotMemoryError, OSError) as exc:
        raise _storage_error(exc) from exc


def _item(record: storage.MemoryRecord) -> HotMemoryItem:
    return HotMemoryItem(
        memory_id=record.memory_id,
        kind=record.kind,  # type: ignore[arg-type]
        title=record.title,
        text=record.text,
        importance=record.importance,
        updated_at=record.updated_at,
        expires_at=record.expires_at,
        related_forkos_ids=list(record.related_forkos_ids),
        revision=record.revision,
    )


def _list_item(record: storage.MemoryRecord, *, now: datetime | None = None) -> HotMemoryListItem:
    return HotMemoryListItem(
        **_item(record).model_dump(),
        status=record.status,  # type: ignore[arg-type]
        effective_status=record.effective_status(now=now),  # type: ignore[arg-type]
        source_mode=record.source_mode,  # type: ignore[arg-type]
        created_at=record.created_at,
        tags=list(record.tags),
        relative_path=record.relative_path,
    )


def _receipt_snapshot(record: storage.MemoryRecord) -> dict[str, Any]:
    """Makbuz için sınırlı künye — gövde KOPYALANMAZ (§98/§129)."""
    return {
        "memory_id": record.memory_id,
        "kind": record.kind,
        "title": record.title,
        "status": record.status,
        "importance": record.importance,
        "expires_at": record.expires_at,
        "revision": record.revision,
        "relative_path": record.relative_path,
    }


def _updated_key(record: storage.MemoryRecord) -> datetime:
    """Kronolojik sıralama anahtarı (§38).

    Ham metin karşılaştırması farklı UTC ofsetlerini YANLIŞ sıralar
    (`2026-09-20T16:00:00+03:00` metinsel olarak `2026-09-20T12:00:00+00:00`dan
    sonra gelir ama aynı ana denk gelir). Bu yüzden damga her zaman farkındal
    `datetime`a çevrilir. Doğrulanmış dosyalarda damga ISO'dur; yine de
    çözülemeyen bir damga sıralamayı düşürmesin diye en eski anahtara düşülür.
    """
    try:
        parsed = storage.parse_iso(record.updated_at)
    except ValueError:
        parsed = None
    return parsed or datetime.min.replace(tzinfo=UTC)


def _stable_rank(records: list[Any], primary: Any = None) -> list[Any]:
    """Kararlı çok geçişli sıralama: öncelik ↓, updated_at ↓, memory_id ↑.

    Python'un `sorted`'ı kararlıdır; bu yüzden kriterleri EN ÖNEMSİZDEN en
    önemliye doğru ayrı geçişlerde uygulamak, tek geçişte tuhaf bir anahtar
    (ör. ters çevrilmiş zaman damgası) uydurmaktan daha okunur ve kesindir.
    Ölçek küçüktür; ek geçişlerin maliyeti yok sayılır.

    `primary` verilirse (ör. arama puanı) en son ve en öncelikli ölçüt olur.
    """
    ordered = sorted(records, key=lambda item: item[1].memory_id)
    ordered.sort(key=lambda item: _updated_key(item[1]), reverse=True)
    if primary is not None:
        ordered.sort(key=lambda item: primary(item))
    else:
        ordered.sort(key=lambda item: -item[1].importance)
    return ordered


def _rank(records: list[storage.MemoryRecord]) -> list[storage.MemoryRecord]:
    """Bağlam/liste sıralaması (§45)."""
    return [record for _, record in _stable_rank([(None, record) for record in records])]


def _invalid_warnings(snapshot: storage.MemorySnapshot) -> list[str]:
    """Geçersiz dosya uyarıları (§46/§47).

    Sır, gövde, frontmatter ya da MUTLAK yol İÇERMEZ; yalnızca sayı söyler.
    Şema dışı ile politika dışı ayrı raporlanır, böylece kullanıcı ne olduğunu
    anlar.
    """
    warnings: list[str] = []
    schema_invalid = snapshot.invalid_count - snapshot.policy_rejected_count
    if schema_invalid:
        warnings.append(f"{schema_invalid} sıcak hafıza dosyası şema dışı; yok sayıldı.")
    if snapshot.policy_rejected_count:
        warnings.append(
            f"{snapshot.policy_rejected_count} sıcak hafıza dosyası politika nedeniyle "
            "dışlandı; sıcak hafızaya yüklenmedi."
        )
    return warnings


# ---------------------------------------------------------------------------
# Okuma: bağlam
# ---------------------------------------------------------------------------


def get_context(
    kinds: list[MemoryKindValue] | None = None,
    *,
    now: datetime | None = None,
) -> HotMemoryContextData:
    """Aktif sıcak hafızayı bütçeye sığdırarak döner (§44-§47).

    Kimlik çakışması varsa fail-closed (`HOT_MEMORY_CONFLICT`): bağlamın
    güvenilir olduğu kanıtlanamıyorsa hiç dönmez (§33).
    """
    root = _read_root()
    snapshot = _scan(root)
    if snapshot.conflicts:
        raise ActionError(
            "HOT_MEMORY_CONFLICT",
            f"aynı memory_id birden fazla dosyada: {', '.join(snapshot.conflict_ids)}",
        )

    wanted = set(kinds) if kinds else set(KIND_ORDER)
    active = [
        record
        for record in snapshot.items
        if record.effective_status(now=now) == "active" and record.kind in wanted
    ]
    active_total = len(active)

    # Sözlük anahtarları MODEL alan adlarıdır ("preferences", "goals" ...);
    # tür adlarıyla ("preference") karıştırmak sessizce boş paket üretirdi.
    buckets: dict[str, list[HotMemoryItem]] = {
        CONTEXT_FIELDS[kind]: [] for kind in KIND_ORDER
    }
    returned = 0
    char_budget = CONTEXT_CHAR_BUDGET

    for kind in KIND_ORDER:
        if kind not in wanted:
            continue
        field = CONTEXT_FIELDS[kind]
        ranked = _rank([record for record in active if record.kind == kind])
        for record in ranked:
            if returned >= CONTEXT_ITEM_CAP:
                break
            if len(buckets[field]) >= KIND_CAPS[kind]:
                break
            cost = len(record.text)
            if cost > char_budget:
                break
            buckets[field].append(_item(record))
            returned += 1
            char_budget -= cost

    omitted = active_total - returned

    return HotMemoryContextData(
        **buckets,
        active_total=active_total,
        returned_total=returned,
        omitted_total=omitted,
        invalid_count=snapshot.invalid_count,
        truncated=omitted > 0,
        warnings=_invalid_warnings(snapshot),
    )


# ---------------------------------------------------------------------------
# Okuma: liste
# ---------------------------------------------------------------------------


def _matches(record: storage.MemoryRecord, needle: str) -> int:
    """Basit leksikal sıralama puanı (§53). 0 = eşleşme yok."""
    title = record.title.casefold()
    text = record.text.casefold()
    tags = [tag.casefold() for tag in record.tags]
    if title == needle:
        return 4
    if any(needle == tag for tag in tags):
        return 3
    if needle in title.split():
        return 2
    if needle in title:
        return 1
    if needle in text:
        return 1
    return 0


def list_memories(
    *,
    kind: MemoryKindValue | None = None,
    effective_status: EffectiveStatusFilter = "active",
    query: str | None = None,
    limit: int = LIST_DEFAULT_LIMIT,
    now: datetime | None = None,
) -> HotMemoryListData:
    """Yönetim/keşif listesi (§52-§54). Çakışmalar fatal değil, raporlanır.

    `query` sınırı MCP şemasında da vardır; ama şema yalnızca ilk savunmadır.
    Doğrudan çağıranlar onu atlayabildiği için sınır burada — YETKİLİ yerde —
    yeniden dayatılır (§26).
    """
    if query is not None and len(query.strip()) > MAX_QUERY_LENGTH:
        raise ActionError(
            "QUERY_TOO_LONG",
            f"arama metni en fazla {MAX_QUERY_LENGTH} karakter olabilir",
        )

    root = _read_root()
    snapshot = _scan(root)

    bounded_limit = max(1, min(int(limit or LIST_DEFAULT_LIMIT), LIST_MAX_LIMIT))
    records = list(snapshot.items)

    if kind is not None:
        records = [record for record in records if record.kind == kind]
    if effective_status != "all":
        records = [
            record
            for record in records
            if record.effective_status(now=now) == effective_status
        ]

    needle = (query or "").strip().casefold()
    if needle:
        scored = [
            (score, record)
            for score, record in ((_matches(record, needle), record) for record in records)
            if score > 0
        ]
        ordered = [record for _, record in _stable_rank(scored, primary=lambda pair: -pair[0])]
    else:
        ordered = _rank(records)

    total = len(ordered)
    page = ordered[:bounded_limit]

    return HotMemoryListData(
        items=[_list_item(record, now=now) for record in page],
        total=total,
        returned=len(page),
        truncated=total > len(page),
        invalid_count=snapshot.invalid_count,
        invalid_paths=list(snapshot.invalid_relative_paths),
        conflict_ids=snapshot.conflict_ids,
    )


# ---------------------------------------------------------------------------
# İlgili kayıt doğrulaması (salt-okunur)
# ---------------------------------------------------------------------------


async def _validate_related_entities(
    session: AsyncSession, related_ids: list[str]
) -> None:
    """İlgili kimlikler AKTİF operasyonel kayıtlar olmalı (§40).

    Salt-okunur: hiçbir Link/Entity satırı oluşturulmaz.
    """
    for raw in related_ids:
        try:
            entity_id = uuid.UUID(raw)
        except ValueError as exc:
            raise ActionError("INVALID_RELATED_ENTITY", f"geçersiz kimlik: {raw!r}") from exc
        entity = await session.get(Entity, entity_id)
        if entity is None:
            raise ActionError("INVALID_RELATED_ENTITY", f"kayıt bulunamadı: {raw}")
        # §34: `note`, `note_folder` VE `note_attachment` (tek kaynak: core/links).
        if entity.type in FROZEN_LEGACY_ENTITY_TYPES:
            raise ActionError(
                "INVALID_RELATED_ENTITY",
                f"dondurulmuş arşiv kaydına bağlanılamaz: {entity.type}",
            )
        if entity.archived_at is not None:
            raise ActionError("INVALID_RELATED_ENTITY", f"arşivlenmiş kayıt: {raw}")


def _reject_obvious_secrets(*parts: str | None) -> None:
    """KOLAYLIK denetimi: sağlanan girdiyi erken reddeder (§6).

    YETKİLİ denetim depolama katmanındadır (`assert_candidate_policy`): orada
    hedefin göreli yolu ve render edilmiş Markdown'ın TAMAMI taranır. Buradaki
    kontrol yalnızca hızlı hata yolu içindir ve alan listesi tutmaz — çağıranlar
    sağlanan girdinin tamamını (serileştirilmiş) geçirir, böylece yeni bir alan
    eklendiğinde denetim sessizce daralmaz.
    """
    if storage.looks_like_secret(*parts):
        raise ActionError(
            "HOT_MEMORY_POLICY_REJECTED",
            "girdi apaçık kimlik bilgisi/anahtar biçimi içeriyor; sıcak hafızaya yazılmaz",
        )


def _verify_current_revision(root, record, expected_revision: str) -> None:
    """Bayat revizyonu, başka her karardan ÖNCE hata yapar (§18/§19).

    Noop kararı "istenen durum mevcut duruma eşit" diye verilir; ama çağıran
    BAYAT bir revizyon gönderdiyse sözleşme gereği `HOT_MEMORY_STALE` kazanır.
    """
    try:
        storage.verify_current_revision(root, record, expected_revision)
    except (storage.HotMemoryError, OSError) as exc:
        raise _storage_error(exc) from exc


# ---------------------------------------------------------------------------
# Yazma: store
# ---------------------------------------------------------------------------


async def store_memory(
    session: AsyncSession,
    data: HotMemoryStoreIn,
    *,
    request_id: str | None = None,
) -> ActionReceipt:
    """Onaylanmış yeni bir sıcak hafıza öğesi oluşturur (§56).

    Kesin tekrar (aynı tür + normalize edilmiş metin) varsa YENİ DOSYA
    açılmaz; mevcut kimlik `noop` makbuzuyla döner (§58).
    """
    _reject_obvious_secrets(data.model_dump_json())
    if data.related_forkos_ids:
        await _validate_related_entities(session, data.related_forkos_ids)

    root = _write_root()
    snapshot = _scan(root)

    needle = storage.normalize_text(data.text)
    for record in snapshot.items:
        # §9: yalnızca AKTİF kayıt yeni bir "hatırla" isteğini bloklar. Emekli
        # ya da süresi geçmiş kayıt yeni bir tarihsel DÖNEMİ engellemez; aksi
        # hâlde kullanıcı açıkça istediği hâlde hiçbir şey aktif olmazdı.
        if (
            record.effective_status() == "active"
            and record.kind == data.kind
            and storage.normalize_text(record.text) == needle
        ):
            return ActionReceipt(
                request_id=request_id,
                tool="hot_memory_store",
                status="noop",
                target_type="hot_memory",
                target_id=record.memory_id,
                summary=f'Hot memory already exists: "{record.title}"',
                before={},
                after=_receipt_snapshot(record),
                warnings=["Aynı tür ve metinle bir kayıt zaten var; yeni dosya oluşturulmadı."],
            )

    try:
        record = storage.create_memory(
            root,
            kind=data.kind,
            title=data.title,
            text=data.text,
            importance=data.importance,
            source_mode=data.source_mode,
            expires_at=data.expires_at,
            related_forkos_ids=data.related_forkos_ids,
            tags=data.tags,
        )
    except (storage.HotMemoryError, OSError) as exc:
        raise _storage_error(exc) from exc

    return ActionReceipt(
        request_id=request_id,
        tool="hot_memory_store",
        status="executed",
        target_type="hot_memory",
        target_id=record.memory_id,
        summary=f'Stored hot memory ({record.kind}): "{record.title}"',
        changed_fields=["created"],
        before={},
        after=_receipt_snapshot(record),
    )


# ---------------------------------------------------------------------------
# Yazma: update
# ---------------------------------------------------------------------------


async def update_memory(
    session: AsyncSession,
    data: HotMemoryUpdateIn,
    *,
    request_id: str | None = None,
) -> ActionReceipt:
    """Var olan öğeyi düzeltir; `expected_revision` uyuşmazsa yazmaz (§60-§63)."""
    root = _write_root()
    snapshot = _scan(root)
    try:
        storage.assert_no_conflict(snapshot, data.memory_id)
        record = storage.find_memory(snapshot, data.memory_id)
    except storage.HotMemoryError as exc:
        raise _to_action_error(exc) from exc
    if record is None:
        raise ActionError("HOT_MEMORY_NOT_FOUND", f"hafıza bulunamadı: {data.memory_id}")

    # §18: bayat revizyon, "değişiklik yok" kararından ÖNCE kazanır. Aksi hâlde
    # çağıran bayat bir `expected_revision` ile sessizce noop makbuzu alırdı.
    _verify_current_revision(root, record, data.expected_revision)

    provided = data.model_fields_set
    # §8: denetim "başlık/gövde değişti mi?" sorusuna BAĞLANMAZ. Güncelleme
    # yalnızca etiketleri değiştirse bile sağlanan girdinin tamamı taranır;
    # ayrıca depolama katmanı sonuç artifact'ını bağımsız olarak doğrular.
    _reject_obvious_secrets(data.model_dump_json())
    if "related_forkos_ids" in provided and data.related_forkos_ids:
        await _validate_related_entities(session, data.related_forkos_ids)

    next_kind = data.kind if "kind" in provided and data.kind else record.kind
    next_title = data.title if "title" in provided and data.title else record.title
    next_text = data.text if "text" in provided and data.text else record.text
    next_importance = (
        data.importance if "importance" in provided and data.importance is not None else record.importance
    )
    clear_expires = "expires_at" in provided and data.expires_at is None
    next_expires = (
        data.expires_at if "expires_at" in provided and data.expires_at else record.expires_at
    )
    next_related = (
        data.related_forkos_ids
        if "related_forkos_ids" in provided and data.related_forkos_ids is not None
        else record.related_forkos_ids
    )
    next_tags = data.tags if "tags" in provided and data.tags is not None else record.tags

    unchanged = (
        next_kind == record.kind
        and next_title == record.title
        and next_text == record.text
        and next_importance == record.importance
        and not clear_expires
        and next_expires == record.expires_at
        and list(next_related) == list(record.related_forkos_ids)
        and list(next_tags) == list(record.tags)
    )
    if unchanged:
        # §63: aynı sonuç için dosya YENİDEN YAZILMAZ (updated_at tazelenmez).
        return ActionReceipt(
            request_id=request_id,
            tool="hot_memory_update",
            status="noop",
            target_type="hot_memory",
            target_id=record.memory_id,
            summary=f'No change for hot memory "{record.title}"',
            before=_receipt_snapshot(record),
            after=_receipt_snapshot(record),
        )

    try:
        updated = storage.rewrite_memory(
            root,
            record,
            expected_revision=data.expected_revision,
            kind=next_kind,
            title=next_title,
            text=next_text,
            importance=next_importance,
            expires_at=next_expires,
            clear_expires_at=clear_expires,
            related_forkos_ids=list(next_related),
            tags=list(next_tags),
        )
    except (storage.HotMemoryError, OSError) as exc:
        raise _storage_error(exc) from exc

    before_snapshot = _receipt_snapshot(record)
    after_snapshot = _receipt_snapshot(updated)
    changed = sorted(
        key for key in after_snapshot if before_snapshot.get(key) != after_snapshot.get(key)
    )
    return ActionReceipt(
        request_id=request_id,
        tool="hot_memory_update",
        status="executed",
        target_type="hot_memory",
        target_id=updated.memory_id,
        summary=f'Updated hot memory "{updated.title}": {", ".join(changed) or "body"}',
        changed_fields=changed,
        before=before_snapshot,
        after=after_snapshot,
    )


# ---------------------------------------------------------------------------
# Yazma: retire
# ---------------------------------------------------------------------------


async def retire_memory(
    session: AsyncSession,
    data: HotMemoryRetireIn,
    *,
    request_id: str | None = None,
) -> ActionReceipt:
    """Öğeyi emekliye ayırır: aktif bağlamdan çıkar, DOSYA SİLİNMEZ (§64/§65)."""
    root = _write_root()
    snapshot = _scan(root)
    try:
        storage.assert_no_conflict(snapshot, data.memory_id)
        record = storage.find_memory(snapshot, data.memory_id)
    except storage.HotMemoryError as exc:
        raise _to_action_error(exc) from exc
    if record is None:
        raise ActionError("HOT_MEMORY_NOT_FOUND", f"hafıza bulunamadı: {data.memory_id}")

    # §19: zaten emekli olsa bile BAYAT revizyon noop'a üstün gelir; yalnızca
    # güncel revizyon "zaten emekli" makbuzu alabilir.
    _verify_current_revision(root, record, data.expected_revision)

    if record.status == "retired":
        return ActionReceipt(
            request_id=request_id,
            tool="hot_memory_retire",
            status="noop",
            target_type="hot_memory",
            target_id=record.memory_id,
            summary=f'Hot memory already retired: "{record.title}"',
            before=_receipt_snapshot(record),
            after=_receipt_snapshot(record),
        )

    try:
        retired = storage.rewrite_memory(
            root,
            record,
            expected_revision=data.expected_revision,
            status="retired",
            retired_reason=data.reason,
        )
    except (storage.HotMemoryError, OSError) as exc:
        raise _storage_error(exc) from exc

    return ActionReceipt(
        request_id=request_id,
        tool="hot_memory_retire",
        status="executed",
        target_type="hot_memory",
        target_id=retired.memory_id,
        summary=f'Retired hot memory "{retired.title}"',
        changed_fields=["status"],
        before=_receipt_snapshot(record),
        after=_receipt_snapshot(retired),
        warnings=["Emeklilik silme değildir: dosya Vault'ta ve Git geçmişinde kalır."],
    )

