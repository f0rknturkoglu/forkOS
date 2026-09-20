"""forkOS → Obsidian Vault bilgi servisi.

Bu modül Vault dosya sistemi davranışının TEK merkezidir: özellik modülleri
(proje, öğrenme, yer imi, hızlı yakalama) doğrudan dosya yazmaz, buradan
geçer. Amaç, bilgi sahipliğinin tek yerde ve denetlenebilir kalmasıdır.

Sözleşme özeti:

  - Yeni bilgi notları Vault'ta yaşar; forkOS `Entity`/`Note`/`Link` satırı
    ÜRETMEZ. Vault dosyası bilgi kaydının kendisidir.
  - Kimlik `forkos_id`'dir; dosya adı ya da klasör yeri kimlik DEĞİLDİR.
    Kullanıcı dosyayı taşısa bile not `forkos_id` ile bulunur.
  - Yazma atomiktir: `O_CREAT|O_EXCL` ile oluşturma, `os.replace` ile
    güncelleme. Sessiz üzerine yazma YOKTUR.
  - Vault yoksa/salt-okunursa işlem AÇIKÇA başarısız olur. Legacy Notes
    tablosuna düşen bir yedek yol yoktur (fail-closed).
  - Hata mesajları ve API yanıtları yalnızca Vault köküne GÖRELİ yol taşır.
"""

from __future__ import annotations

import contextlib
import os
import uuid
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity
from app.core.time import local_today
from app.integrations.obsidian.constants import (
    ALLOWED_FORKOS_TYPES,
    ENTITY_KNOWLEDGE_TARGETS,
    INBOX_ROOT,
    JOURNAL_FOLDER,
    NOTE_KIND_DAILY,
    NOTE_KIND_PERSONAL,
    NOTE_KIND_PROJECT_JOURNAL,
    PROJECTS_ROOT,
    RELATED_ENTITY_NOTE_TYPES,
    TYPE_DEFAULT_FOLDERS,
)
from app.integrations.obsidian.frontmatter import (
    parse_frontmatter,
    render_markdown_with_frontmatter,
)
from app.integrations.obsidian.index import VaultIndex, item_from_frontmatter
from app.integrations.obsidian.models import VaultItem, VaultStatus
from app.integrations.obsidian.security import resolve_safe_vault_path, sanitize_filename
from app.integrations.obsidian.uri import (
    daily_note_uri,
    open_vault_uri,
    search_uri,
)
from app.integrations.obsidian.vault import require_writable_vault, vault_context

#: Deterministik çakışma çözümü: aynı taban yol doluysa dosya adına forkOS
#: kimliğinin kısaltılmış öneki eklenir. Sıraya bağlı "(1)" ÜRETİLMEZ.
_SUFFIX_WIDTHS: tuple[int, ...] = (8, 12, 16, 32)

#: Gövdeden türetilen başlığın üst sınırı.
_MAX_DERIVED_TITLE = 80


class VaultConflictError(Exception):
    """Belirtilen forkOS ID'si Vault içinde birden fazla dosyada tespit edildiğinde fırlatılır."""

    def __init__(self, forkos_id: str, conflicting_paths: list[str]) -> None:
        self.forkos_id = forkos_id
        self.conflicting_paths = conflicting_paths
        super().__init__(
            f"Vault içinde '{forkos_id}' kimliğine sahip birden fazla dosya bulundu: {conflicting_paths}"
        )


class VaultWriteError(Exception):
    """Deterministik adayların tümü dolduğu için dosya güvenle yazılamadı."""


class VaultStaleWriteError(Exception):
    """Dosya, çağıranın beklediği sürümden sonra değişmiş; körü körüne yazılmaz."""


vault_index = VaultIndex()


def _status_with_uris(status: VaultStatus, vault_name: str) -> VaultStatus:
    """Duruma Obsidian bağlantılarını ekler (istemci URI kurmaz)."""
    if not status.configured:
        return status
    daily_uri = daily_note_uri(vault_name)
    managed_daily = vault_index.find_by_note_kind(
        NOTE_KIND_DAILY, journal_day=local_today().isoformat()
    )
    if managed_daily is not None:
        daily_uri = managed_daily.open_uri
    status.open_uri = open_vault_uri(vault_name)
    # Obsidian klasör açan resmi bir URI sunmaz; Inbox'ı göstermenin güvenilir
    # yolu klasörle sınırlı aramadır. Dosya UYDURULMAZ.
    status.inbox_uri = search_uri(vault_name, f'path:"{INBOX_ROOT}/"')
    status.daily_uri = daily_uri
    return status


def get_vault_status(
    vault_path_override: Path | None = None,
    vault_name_override: str | None = None,
) -> VaultStatus:
    v_root, v_name = vault_context(vault_path_override, vault_name_override)
    return _status_with_uris(vault_index.current_status(v_root, v_name), v_name)


def refresh_vault_index(
    vault_path_override: Path | None = None,
    vault_name_override: str | None = None,
) -> VaultStatus:
    v_root, v_name = vault_context(vault_path_override, vault_name_override)
    return _status_with_uris(vault_index.scan(v_root, v_name), v_name)


def vault_search_uri(query: str) -> str:
    _, v_name = vault_context()
    return search_uri(v_name, query)


def _ensure_index_scanned() -> None:
    if not vault_index.is_scanned:
        refresh_vault_index()


def _assert_not_conflicted(forkos_id: str) -> None:
    """Aynı kimlik iki dosyada varsa HİÇBİR yazma yapılmaz (fail-closed)."""
    _ensure_index_scanned()
    if vault_index.is_conflicted(forkos_id):
        raise VaultConflictError(forkos_id, vault_index.conflicts[forkos_id])


def resolve_managed_item(
    forkos_id: str | uuid.UUID,
    vault_path_override: Path | None = None,
    vault_name_override: str | None = None,
) -> VaultItem | None:
    """`forkos_id` ile managed dosyayı bulur (dosya adına güvenilmez)."""
    fid = str(forkos_id)
    if not vault_index.is_scanned:
        refresh_vault_index(vault_path_override, vault_name_override)

    if vault_index.is_conflicted(fid):
        raise VaultConflictError(fid, vault_index.conflicts[fid])

    item = vault_index.get_item(fid)
    if item:
        v_root, _ = vault_context(vault_path_override, vault_name_override)
        if v_root:
            try:
                real_file = resolve_safe_vault_path(v_root, item.relative_path)
                if not real_file.is_file():
                    # Dosya taşınmış veya silinmişse yeniden tara
                    refresh_vault_index(vault_path_override, vault_name_override)
                    if vault_index.is_conflicted(fid):
                        raise VaultConflictError(fid, vault_index.conflicts[fid])
                    return vault_index.get_item(fid)
            except VaultConflictError:
                raise
            except Exception:
                return None
    return item


def forkos_type_for_entity(entity_type: str) -> str:
    target = ENTITY_KNOWLEDGE_TARGETS.get(entity_type)
    if target is None:
        raise ValueError(f"Bu kayıt tipi için bilgi notu tanımlı değil: '{entity_type}'")
    return target[0]


def derive_title(body: str) -> str:
    """Gövdeden okunabilir bir başlık türetir (ilk anlamlı satır)."""
    for raw_line in (body or "").splitlines():
        line = raw_line.strip().lstrip("#").lstrip(">").strip()
        line = line.strip("*_`").strip()
        if line:
            return sanitize_filename(line[:_MAX_DERIVED_TITLE])
    return "Untitled"


def _created_frontmatter(forkos_id: str | uuid.UUID, forkos_type: str, **extra: object) -> dict:
    """Yeni managed notun iskelet frontmatter'ı.

    Kimlik ve tip HER ZAMAN metne çevrilir: `uuid.UUID` nesnesi YAML
    dumper'ının temsil edemeyeceği bir tiptir ve dosya yazımı patlar.
    """
    now_iso = datetime.now(UTC).isoformat()
    metadata: dict = {
        "forkos_id": str(forkos_id),
        "forkos_type": str(forkos_type),
        "forkos_created_at": now_iso,
        "forkos_updated_at": now_iso,
    }
    metadata.update({key: value for key, value in extra.items() if value is not None})
    return metadata


def _default_body_for_type(forkos_type: str, title: str) -> str:
    if forkos_type == "project":
        return (
            f"# {title}\n\n"
            "## Amaç\n\n"
            "## Şu anki durum\n\n"
            "## Kararlar\n\n"
            "## Araştırma\n\n"
            "## Referanslar\n"
        )
    if forkos_type == "learning":
        return f"# {title}\n\n## Notlar\n\n## Kavramlar\n\n## Sorular\n\n## Kaynaklar\n"
    if forkos_type == "source":
        return f"# {title}\n\n## Notlar\n\n## Öne çıkanlar\n"
    return f"# {title}\n"


def _write_new_file(
    *,
    target_dir: Path,
    stem: str,
    metadata: dict,
    body: str,
    resolved_root: Path,
    v_name: str,
) -> VaultItem:
    """Deterministik aday sırasıyla atomik oluşturma; asla üzerine yazmaz."""
    forkos_id = str(metadata["forkos_id"])
    content = render_markdown_with_frontmatter(metadata, body)
    target_dir.mkdir(parents=True, exist_ok=True)

    suffix = uuid.UUID(forkos_id).hex
    candidates = [f"{stem}.md"]
    candidates.extend(f"{stem}--{suffix[:width]}.md" for width in _SUFFIX_WIDTHS)

    for candidate_name in candidates:
        candidate_file = target_dir / candidate_name
        try:
            fd = os.open(candidate_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            continue
        try:
            with open(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
        except Exception:
            with contextlib.suppress(OSError):
                candidate_file.unlink(missing_ok=True)
            raise

        rel_path = str(candidate_file.relative_to(resolved_root)).replace("\\", "/")
        stat = candidate_file.stat()
        # İndekse yazılan frontmatter'dan TÜRETİLEN kaydı koy: tarama ile
        # aynı sonucu verir, alan eşlemesi iki yerde tekrar etmez.
        item = item_from_frontmatter(
            frontmatter=metadata,
            body=body,
            relative_path=rel_path,
            vault_name=v_name,
            mtime=stat.st_mtime,
            size=stat.st_size,
        )
        vault_index.add_or_update_item(item)
        return item

    raise VaultWriteError(f"'{stem}' için boş bir dosya adı bulunamadı (Vault'ta çok fazla çakışma)")


def _relation_entry(target: Entity, relation: str = "notes_about") -> dict:
    """İlişki metadata'sı SUNUCUDA çözülür; istemcinin tip/başlığına güvenilmez."""
    return {
        "relation": relation,
        "target_id": str(target.id),
        "target_type": target.type,
        "target_title": target.title,
    }


async def capture_knowledge_note(
    session: AsyncSession,
    *,
    body: str,
    title: str | None = None,
    relate_to: uuid.UUID | None = None,
    tags: list[str] | None = None,
) -> VaultItem:
    """Hızlı yakalama: `00 Inbox/` altında yeni bilgi notu.

    Kimliği sunucu üretir; `Entity`/`Note`/`Link` satırı OLUŞTURULMAZ. İlişki
    bilgisi yalnızca frontmatter'a yazılır.
    """
    resolved_root, v_name = require_writable_vault()
    clean_body = (body or "").strip()
    if not clean_body:
        raise ValueError("Not gövdesi boş olamaz")

    forkos_id = str(uuid.uuid4())
    note_title = sanitize_filename(title) if title and title.strip() else derive_title(clean_body)

    metadata = _created_frontmatter(
        forkos_id,
        "note",
        forkos_note_kind=NOTE_KIND_PERSONAL,
        title=note_title,
        forkos_captured_from="forkOS",
    )
    if relate_to is not None:
        target = await session.get(Entity, relate_to)
        if target is None:
            raise ValueError("İlişkilendirilecek kayıt bulunamadı")
        metadata["forkos_relations"] = [_relation_entry(target)]
    if tags:
        metadata["tags"] = [tag.strip() for tag in tags if tag and tag.strip()]

    return _write_new_file(
        target_dir=resolve_safe_vault_path(resolved_root, INBOX_ROOT),
        stem=note_title,
        metadata=metadata,
        body=clean_body,
        resolved_root=resolved_root,
        v_name=v_name,
    )


def create_managed_note(
    forkos_id: uuid.UUID | str,
    forkos_type: str,
    title: str,
    target_folder: str | None = None,
    initial_body: str | None = None,
) -> VaultItem:
    """Kimliği ÇAĞIRANIN verdiği managed notu oluşturur (düşük seviye).

    Ürün akışları bunu kullanmaz: hızlı yakalama `capture_knowledge_note`,
    kayda bağlı kanonik notlar `ensure_entity_knowledge_note` üzerinden gider
    ve kimliği sunucu üretir. Bu giriş noktası, kimliği zaten bilinen bir
    kaydı (ör. göç testleri ve tanılama) önceden oluşturmak içindir.

    Idempotenttir: aynı `forkos_id` zaten varsa dosya yeniden yazılmaz.
    """
    clean_type = str(forkos_type).strip().lower()
    if clean_type not in ALLOWED_FORKOS_TYPES:
        raise ValueError(
            f"Desteklenmeyen forkos_type: '{forkos_type}'. İzin verilenler: {sorted(ALLOWED_FORKOS_TYPES)}"
        )

    str_id = str(forkos_id)
    _assert_not_conflicted(str_id)

    existing = resolve_managed_item(str_id)
    if existing is not None:
        return existing

    resolved_root, v_name = require_writable_vault()

    clean_title = sanitize_filename(title)
    metadata = _created_frontmatter(str_id, clean_type, title=clean_title)
    body = (
        initial_body
        if initial_body is not None
        else _default_body_for_type(clean_type, clean_title)
    )

    folder = target_folder or TYPE_DEFAULT_FOLDERS.get(clean_type, INBOX_ROOT)
    folder_rel = folder
    if clean_type == "project":
        # Kanonik proje yerleşimi: 20 Projects/<Proje>/<Proje>.md
        stripped = folder.rstrip("/")
        if not (stripped.endswith(f"/{clean_title}") or stripped == clean_title):
            folder_rel = f"{stripped}/{clean_title}"

    return _write_new_file(
        target_dir=resolve_safe_vault_path(resolved_root, folder_rel),
        stem=clean_title,
        metadata=metadata,
        body=body,
        resolved_root=resolved_root,
        v_name=v_name,
    )


async def ensure_entity_knowledge_note(
    session: AsyncSession,
    forkos_id: uuid.UUID,
    *,
    initial_body: str | None = None,
    source_url: str | None = None,
) -> VaultItem:
    """Kanonik bilgi notunu (varsa) çözer, yoksa oluşturur.

    Kimlik entity UUID'sidir: aynı çağrı ikinci kez yapıldığında YENİ dosya
    üretilmez. Başlık ve tip istemciden alınmaz; `entity` tablosundan çözülür.

    `source_url` yalnızca kaynak notlarında (`forkos_type == "source"`)
    kullanılan künyedir; PHASE 2 göçünün yazdığı anahtarlarla aynıdır, böylece
    yeni ve taşınmış kaynak notları tek şemayla okunur.
    """
    entity = await session.get(Entity, forkos_id)
    if entity is None:
        raise ValueError("Kayıt bulunamadı")

    target = ENTITY_KNOWLEDGE_TARGETS.get(entity.type)
    if target is None:
        raise ValueError(f"Bu kayıt tipi için bilgi notu tanımlı değil: '{entity.type}'")

    forkos_type, folder = target

    existing = resolve_managed_item(forkos_id)
    if existing is not None:
        return existing

    resolved_root, v_name = require_writable_vault()

    metadata = _created_frontmatter(
        forkos_id,
        forkos_type,
        title=entity.title,
        forkos_entity_type=entity.type,
    )
    if forkos_type in RELATED_ENTITY_NOTE_TYPES:
        metadata["forkos_relations"] = [_relation_entry(entity)]
    if forkos_type == "source":
        metadata["forkos_source_bookmark_id"] = str(forkos_id)
        metadata["source_title"] = entity.title
        if source_url:
            metadata["source"] = source_url
    body = (
        initial_body
        if initial_body is not None
        else _default_body_for_type(forkos_type, entity.title)
    )

    stem = sanitize_filename(entity.title)
    # Kanonik proje yerleşimi: 20 Projects/<Proje>/<Proje>.md
    folder_rel = f"{folder.rstrip('/')}/{stem}" if forkos_type == "project" else folder

    return _write_new_file(
        target_dir=resolve_safe_vault_path(resolved_root, folder_rel),
        stem=stem,
        metadata=metadata,
        body=body,
        resolved_root=resolved_root,
        v_name=v_name,
    )


async def ensure_project_journal(
    session: AsyncSession,
    project_id: uuid.UUID,
    day: date,
) -> VaultItem:
    """Proje günlüğünün Vault dosyasını çözer, yoksa oluşturur.

    PHASE 2 ile taşınmış günlükler `forkos_id`'leriyle YENİDEN KULLANILIR;
    aynı gün için ikinci dosya üretilmez.
    """
    project = await session.get(Entity, project_id)
    if project is None:
        raise ValueError("Proje bulunamadı")

    resolved_root, v_name = require_writable_vault()
    _ensure_index_scanned()

    day_iso = day.isoformat()
    migrated = vault_index.find_by_note_kind(
        NOTE_KIND_PROJECT_JOURNAL, project_id=str(project_id), journal_day=day_iso
    )
    if migrated is not None:
        return migrated

    # Proje bilgi notu varsa günlük ONUN klasörüne yazılır: kullanıcı proje
    # klasörünü yeniden adlandırdıysa yeni bir ağaç açılmaz (§24).
    project_note = resolve_managed_item(project_id)
    parent = str(Path(project_note.relative_path).parent) if project_note is not None else ""
    if parent and parent != ".":
        folder_rel = f"{parent}/{JOURNAL_FOLDER}"
    else:
        folder_rel = f"{PROJECTS_ROOT}/{sanitize_filename(project.title)}/{JOURNAL_FOLDER}"

    forkos_id = str(uuid.uuid4())
    metadata = _created_frontmatter(
        forkos_id,
        "note",
        forkos_note_kind=NOTE_KIND_PROJECT_JOURNAL,
        title=day_iso,
        forkos_project_id=str(project_id),
        forkos_journal_day=day_iso,
        forkos_relations=[_relation_entry(project)],
    )

    return _write_new_file(
        target_dir=resolve_safe_vault_path(resolved_root, folder_rel),
        stem=day_iso,
        metadata=metadata,
        body=f"# {day_iso}\n",
        resolved_root=resolved_root,
        v_name=v_name,
    )


def read_managed_note_body(forkos_id: str | uuid.UUID) -> tuple[VaultItem, str] | None:
    """Managed dosyanın gövdesini (frontmatter hariç) okur."""
    item = resolve_managed_item(forkos_id)
    if item is None:
        return None
    v_root, _ = vault_context()
    if v_root is None:
        raise RuntimeError("Obsidian Vault yapılandırılmamış (OBSIDIAN_VAULT_PATH boş)")
    real_file = resolve_safe_vault_path(v_root, item.relative_path)
    if not real_file.is_file():
        return None
    frontmatter, body = parse_frontmatter(real_file.read_text(encoding="utf-8", errors="replace"))
    if frontmatter is None:
        return None
    return item, body


def update_managed_note_body(
    forkos_id: str | uuid.UUID,
    body: str,
    *,
    expected_mtime: float,
) -> VaultItem:
    """Managed dosyanın gövdesini atomik olarak değiştirir.

    Kurallar:
      - Bilinmeyen/kullanıcıya ait frontmatter alanları AYNEN korunur.
      - `expected_mtime` eşleşmezse yazma reddedilir (kullanıcı düzenlemesini
        körü körüne ezmemek için).
      - Çakışmalı dosya hiçbir koşulda değiştirilmez.
    """
    item = resolve_managed_item(forkos_id)
    if item is None:
        raise ValueError("Vault içinde bu kimliğe sahip yönetilen not bulunamadı")

    resolved_root, v_name = require_writable_vault()
    real_file = resolve_safe_vault_path(resolved_root, item.relative_path)
    if not real_file.is_file():
        raise ValueError("Vault dosyası bulunamadı; indeksi yenile")

    current = real_file.read_text(encoding="utf-8", errors="replace")
    frontmatter, _ = parse_frontmatter(current)
    if frontmatter is None:
        raise ValueError("Dosya forkOS frontmatter'ı içermiyor; güvenli güncelleme yapılamaz")

    if abs(real_file.stat().st_mtime - expected_mtime) > 1e-6:
        raise VaultStaleWriteError(
            "Dosya son okumadan sonra değişmiş; güncelleme yapılmadı (önce yenile)"
        )

    metadata = dict(frontmatter)
    metadata["forkos_updated_at"] = datetime.now(UTC).isoformat()

    temp_file = real_file.with_name(f".{real_file.name}.forkos-{uuid.uuid4().hex}.tmp")
    try:
        temp_file.write_text(render_markdown_with_frontmatter(metadata, body), encoding="utf-8")
        os.replace(temp_file, real_file)
    except Exception:
        with contextlib.suppress(OSError):
            temp_file.unlink(missing_ok=True)
        raise

    stat = real_file.stat()
    updated = item.model_copy(update={"mtime": stat.st_mtime, "size": stat.st_size})
    vault_index.add_or_update_item(updated)
    return updated
