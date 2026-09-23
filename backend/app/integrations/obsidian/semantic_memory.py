"""A4: f0rknbrain dayanıklı anlamsal hafıza depolama katmanı (`30 Knowledge/Memory/`).

Bu servis dayanıklı anlamsal bilgi kartlarının (`forkos_type=note`, `forkos_note_kind=semantic_memory`)
kasa üzerindeki yaşam döngüsünü yönetir:
- Atomik ve üzerine yazmayan kart oluşturma (O_EXCL / hardlink)
- Sır ve kimlik bilgisi güvenlik denetimi (secret safety)
- İnsana okunabilir ve Obsidian içinde düzenlenebilir Markdown biçimi
- Kart revizyonu (SHA-256) ve bayat yazma koruması
- Eklemeli (additive) bellek modeli: türetilmiş `superseded` efektif durumu
- A2 önyüklemesi için sınırlı `SemanticProfile` görünümü
"""

from __future__ import annotations

import contextlib
import errno
import hashlib
import logging
import os
import re
import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from app.core.secret_safety import contains_high_confidence_secret
from app.integrations.obsidian.constants import (
    NOTE_KIND_SEMANTIC_MEMORY,
    SEMANTIC_MEMORY_ROOT,
)
from app.integrations.obsidian.frontmatter import (
    parse_frontmatter,
    render_markdown_with_frontmatter,
)
from app.integrations.obsidian.security import resolve_safe_vault_path

LOGGER = logging.getLogger("forkos.semantic_memory")

SemanticMemoryKind = Literal[
    "identity",
    "preference",
    "correction",
    "constraint",
    "goal",
    "decision",
    "lesson",
    "project_knowledge",
    "reference",
]

SemanticEvidenceClass = Literal[
    "explicit_user",
    "canonical_source",
    "episode_derived",
    "model_derived",
]

SemanticMemoryStatus = Literal["active", "retired"]
SemanticEffectiveStatus = Literal["active", "superseded", "retired", "expired"]

_NO_HARDLINK_ERRNOS = frozenset({errno.EXDEV, errno.EPERM, errno.ENOTSUP, errno.EOPNOTSUPP})


class SemanticStorageError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class SemanticMemoryCard:
    """f0rknbrain kasasındaki tekil dayanıklı anlamsal kart."""

    card_id: str
    kind: str
    title: str
    statement: str
    scope: str
    scope_project: str | None
    subject_key: str | None
    domains: list[str]
    status: str
    observed_at: datetime
    valid_from: datetime | None
    valid_to: datetime | None
    evidence_class: str
    evidence_refs: list[str]
    supersedes: list[str]
    sensitivity: str
    remote_allowed: bool
    conditions: list[str]
    exceptions: list[str]
    rationale: str | None
    created_at: datetime
    updated_at: datetime
    revision: str
    relative_path: str
    effective_status: str = "active"


@dataclass(frozen=True)
class SemanticProfile:
    """A2 önyüklemesi için aktif kartlardan türetilmiş hafif görünüm."""

    corrections: list[SemanticMemoryCard] = field(default_factory=list)
    constraints: list[SemanticMemoryCard] = field(default_factory=list)
    identity: list[SemanticMemoryCard] = field(default_factory=list)
    goals: list[SemanticMemoryCard] = field(default_factory=list)
    preferences: list[SemanticMemoryCard] = field(default_factory=list)


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.isoformat()


def _parse_dt(val: Any) -> datetime | None:
    if not val:
        return None
    if isinstance(val, datetime):
        return val if val.tzinfo is not None else val.replace(tzinfo=UTC)
    try:
        dt = datetime.fromisoformat(str(val))
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)
    except Exception:
        return None


def render_card_markdown(
    *,
    card_id: str,
    kind: str,
    title: str,
    statement: str,
    scope: str = "global",
    scope_project: str | None = None,
    subject_key: str | None = None,
    domains: list[str] | None = None,
    status: str = "active",
    observed_at: datetime,
    valid_from: datetime | None = None,
    valid_to: datetime | None = None,
    evidence_class: str = "episode_derived",
    evidence_refs: list[str] | None = None,
    supersedes: list[str] | None = None,
    sensitivity: str = "normal",
    remote_allowed: bool = False,
    conditions: list[str] | None = None,
    exceptions: list[str] | None = None,
    rationale: str | None = None,
    created_at: datetime | None = None,
    updated_at: datetime | None = None,
) -> str:
    """Kalıcı hafıza kartının frontmatter ve Markdown gövdesini oluşturur."""
    now = datetime.now(UTC)
    c_at = created_at or now
    u_at = updated_at or now

    frontmatter = {
        "forkos_id": card_id,
        "forkos_type": "note",
        "forkos_note_kind": NOTE_KIND_SEMANTIC_MEMORY,
        "forkos_created_at": _iso(c_at),
        "forkos_updated_at": _iso(u_at),
        "forkos_memory_kind": kind,
        "forkos_memory_scope": scope,
        "forkos_memory_scope_id": scope_project,
        "forkos_memory_subject_key": subject_key,
        "forkos_memory_domains": list(domains or []),
        "forkos_memory_status": status,
        "forkos_memory_observed_at": _iso(observed_at),
        "forkos_memory_valid_from": _iso(valid_from),
        "forkos_memory_valid_to": _iso(valid_to),
        "forkos_memory_evidence_class": evidence_class,
        "forkos_memory_evidence_refs": [
            str(r.get("ref") or r) if isinstance(r, dict) else str(r)
            for r in (evidence_refs or [])
        ],
        "forkos_memory_supersedes": list(supersedes or []),
        "forkos_memory_sensitivity": sensitivity,
        "forkos_memory_remote_allowed": remote_allowed,
    }

    body_lines: list[str] = [f"# {title}", "", "## İfade", statement.strip()]

    conds = [c.strip() for c in (conditions or []) if c.strip()]
    if conds:
        body_lines.extend(["", "## Koşullar"] + [f"- {c}" for c in conds])

    excs = [e.strip() for e in (exceptions or []) if e.strip()]
    if excs:
        body_lines.extend(["", "## İstisnalar"] + [f"- {e}" for e in excs])

    if rationale and rationale.strip():
        body_lines.extend(["", "## Gerekçe", rationale.strip()])

    body_lines.append("")
    return render_markdown_with_frontmatter(frontmatter, "\n".join(body_lines))


def parse_card_markdown(content: str, relative_path: str) -> SemanticMemoryCard | None:
    """Markdown metninden SemanticMemoryCard nesnesi ayrıştırır."""
    meta, body = parse_frontmatter(content)
    if meta.get("forkos_note_kind") != NOTE_KIND_SEMANTIC_MEMORY:
        return None

    card_id = meta.get("forkos_id")
    if not card_id or not isinstance(card_id, str):
        return None

    kind = str(meta.get("forkos_memory_kind") or "reference")
    scope = str(meta.get("forkos_memory_scope") or "global")
    scope_proj = meta.get("forkos_memory_scope_id")
    subject_key = meta.get("forkos_memory_subject_key")
    domains = list(meta.get("forkos_memory_domains") or [])
    status = str(meta.get("forkos_memory_status") or "active")
    observed_at = _parse_dt(meta.get("forkos_memory_observed_at")) or _parse_dt(meta.get("forkos_created_at")) or datetime.now(UTC)
    valid_from = _parse_dt(meta.get("forkos_memory_valid_from"))
    valid_to = _parse_dt(meta.get("forkos_memory_valid_to"))
    evidence_class = str(meta.get("forkos_memory_evidence_class") or "episode_derived")
    evidence_refs = [str(r) for r in (meta.get("forkos_memory_evidence_refs") or [])]
    supersedes = [str(s) for s in (meta.get("forkos_memory_supersedes") or [])]
    sensitivity = str(meta.get("forkos_memory_sensitivity") or "normal")
    remote_allowed = bool(meta.get("forkos_memory_remote_allowed") or False)
    created_at = _parse_dt(meta.get("forkos_created_at")) or observed_at
    updated_at = _parse_dt(meta.get("forkos_updated_at")) or created_at

    # Gövde bölümlerini çıkar
    title = ""
    statement = ""
    conditions: list[str] = []
    exceptions: list[str] = []
    rationale: str | None = None

    current_section: str | None = None
    section_lines: list[str] = []

    def commit_section(section: str | None, lines: list[str]) -> None:
        nonlocal statement, conditions, exceptions, rationale
        text = "\n".join(lines).strip()
        if not section:
            return
        if section == "ifade":
            statement = text
        elif section == "kosullar":
            conditions = [
                re.sub(r"^[-*]\s*", "", line).strip()
                for line in lines
                if line.strip() and line.strip().startswith(("-", "*"))
            ]
        elif section == "istisnalar":
            exceptions = [
                re.sub(r"^[-*]\s*", "", line).strip()
                for line in lines
                if line.strip() and line.strip().startswith(("-", "*"))
            ]
        elif section == "gerekce":
            rationale = text or None

    for raw_line in body.splitlines():
        line = raw_line.strip()
        if line.startswith("# ") and not title:
            title = line[2:].strip()
            continue
        if line.startswith("## "):
            commit_section(current_section, section_lines)
            section_lines = []
            sec_header = unicodedata.normalize("NFKC", line[3:].strip().replace("İ", "i").replace("I", "ı")).lower()
            if "ifade" in sec_header:
                current_section = "ifade"
            elif "koşul" in sec_header or "kosul" in sec_header:
                current_section = "kosullar"
            elif "istisna" in sec_header:
                current_section = "istisnalar"
            elif "gerekçe" in sec_header or "gerekce" in sec_header:
                current_section = "gerekce"
            else:
                current_section = None
            continue
        if current_section:
            section_lines.append(raw_line)

    commit_section(current_section, section_lines)
    if not statement:
        statement = body.strip()
    if not title:
        title = statement[:60]

    revision = hashlib.sha256(content.encode("utf-8")).hexdigest()

    return SemanticMemoryCard(
        card_id=card_id,
        kind=kind,
        title=title,
        statement=statement,
        scope=scope,
        scope_project=str(scope_proj) if scope_proj else None,
        subject_key=str(subject_key) if subject_key else None,
        domains=domains,
        status=status,
        observed_at=observed_at,
        valid_from=valid_from,
        valid_to=valid_to,
        evidence_class=evidence_class,
        evidence_refs=evidence_refs,
        supersedes=supersedes,
        sensitivity=sensitivity,
        remote_allowed=remote_allowed,
        conditions=conditions,
        exceptions=exceptions,
        rationale=rationale,
        created_at=created_at,
        updated_at=updated_at,
        revision=revision,
        relative_path=relative_path,
        effective_status="active",
    )


def assert_secret_safety(content: str) -> None:
    """Yazma öncesi sır sızıntısı denetimi."""
    if contains_high_confidence_secret(content):
        raise SemanticStorageError("SECRET_LEAKAGE", "İçerik yüksek güvenilirlikli sır veya parola içeriyor")


def _write_temp(target: Path, content: str) -> Path:
    temp = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
    try:
        with open(temp, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        with contextlib.suppress(OSError):
            temp.unlink(missing_ok=True)
        raise
    return temp


def _create_exclusive(target: Path, content: str) -> None:
    """Yeni hedefi atomik ve üzerine yazmadan yayınlar."""
    temp = _write_temp(target, content)
    try:
        try:
            os.link(temp, target)
        except FileExistsError as exc:
            raise SemanticStorageError(
                "SEMANTIC_CARD_CONFLICT", f"aynı kimlikle dosya zaten var: {target.name}"
            ) from exc
        except OSError as exc:
            if exc.errno not in _NO_HARDLINK_ERRNOS:
                raise
            # Fallback
            fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            with open(fd, "w", encoding="utf-8") as handle:
                handle.write(content)
    finally:
        with contextlib.suppress(OSError):
            temp.unlink(missing_ok=True)


def create_semantic_card(
    vault_root: Path,
    *,
    card_id: str | None = None,
    kind: str,
    title: str,
    statement: str,
    scope: str = "global",
    scope_project: str | None = None,
    subject_key: str | None = None,
    domains: list[str] | None = None,
    status: str = "active",
    observed_at: datetime | None = None,
    valid_from: datetime | None = None,
    valid_to: datetime | None = None,
    evidence_class: str = "episode_derived",
    primary_evidence_class: str | None = None,
    evidence_refs: list[Any] | None = None,
    supersedes: list[str] | None = None,
    sensitivity: str = "normal",
    remote_allowed: bool = False,
    conditions: list[str] | None = None,
    exceptions: list[str] | None = None,
    rationale: str | None = None,
) -> SemanticMemoryCard:
    """30 Knowledge/Memory/ altına yeni bir dayanıklı hafıza kartı yazar."""
    if not vault_root.is_dir() or not os.access(vault_root, os.W_OK):
        raise SemanticStorageError("VAULT_READONLY", "Obsidian Vault dizinine yazma izni yok")

    cid = card_id or str(uuid.uuid4())
    filename = f"{cid}.md"
    rel_path = f"{SEMANTIC_MEMORY_ROOT}/{filename}"

    target = resolve_safe_vault_path(vault_root, rel_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    obs_at = observed_at or datetime.now(UTC)
    now = datetime.now(UTC)

    eff_evidence_class = primary_evidence_class or evidence_class

    content = render_card_markdown(
        card_id=cid,
        kind=kind,
        title=title,
        statement=statement,
        scope=scope,
        scope_project=scope_project,
        subject_key=subject_key,
        domains=domains,
        status=status,
        observed_at=obs_at,
        valid_from=valid_from,
        valid_to=valid_to,
        evidence_class=eff_evidence_class,
        evidence_refs=evidence_refs,
        supersedes=supersedes,
        sensitivity=sensitivity,
        remote_allowed=remote_allowed,
        conditions=conditions,
        exceptions=exceptions,
        rationale=rationale,
        created_at=now,
        updated_at=now,
    )

    assert_secret_safety(content)
    _create_exclusive(target, content)

    card = parse_card_markdown(content, rel_path)
    if card is None:
        raise SemanticStorageError("PARSE_FAILED", "Kart yazıldı ancak geri ayrıştırılamadı")
    return card


def read_semantic_card(vault_root: Path, card_id: str) -> SemanticMemoryCard | None:
    """Belirli bir card_id'ye sahip kartı okur."""
    rel_path = f"{SEMANTIC_MEMORY_ROOT}/{card_id}.md"
    try:
        path = resolve_safe_vault_path(vault_root, rel_path)
        if not path.is_file():
            return None
        content = path.read_text(encoding="utf-8")
        return parse_card_markdown(content, rel_path)
    except Exception:
        return None


def scan_semantic_cards(vault_root: Path) -> list[SemanticMemoryCard]:
    """30 Knowledge/Memory/ altındaki tüm kartları tarar ve efektif durumlarını çözer."""
    root_path = vault_root / SEMANTIC_MEMORY_ROOT
    if not root_path.is_dir():
        return []

    cards: list[SemanticMemoryCard] = []
    for entry in sorted(root_path.glob("*.md")):
        if entry.name.startswith("."):
            continue
        rel_path = f"{SEMANTIC_MEMORY_ROOT}/{entry.name}"
        try:
            content = entry.read_text(encoding="utf-8")
            card = parse_card_markdown(content, rel_path)
            if card:
                cards.append(card)
        except Exception as exc:
            LOGGER.warning("Kart okunamadı (%s): %s", entry.name, exc)

    return derive_effective_status(cards)


def derive_effective_status(cards: list[SemanticMemoryCard]) -> list[SemanticMemoryCard]:
    """Kartların birbirini geçersiz kılma (supersession) ve süre durumlarını çözer."""
    superseded_ids: set[str] = set()
    now = datetime.now(UTC)

    # 1. Aşama: Aktif kartların supersedes listelerini topla
    for card in cards:
        if card.status == "active" and (card.valid_to is None or card.valid_to >= now):
            superseded_ids.update(card.supersedes)

    # 2. Aşama: Efektif durumları ata
    resolved: list[SemanticMemoryCard] = []
    for card in cards:
        eff_status: SemanticEffectiveStatus = "active"
        if card.status == "retired":
            eff_status = "retired"
        elif card.card_id in superseded_ids:
            eff_status = "superseded"
        elif card.valid_to and card.valid_to < now:
            eff_status = "expired"

        if eff_status != card.effective_status:
            card = SemanticMemoryCard(
                card_id=card.card_id,
                kind=card.kind,
                title=card.title,
                statement=card.statement,
                scope=card.scope,
                scope_project=card.scope_project,
                subject_key=card.subject_key,
                domains=card.domains,
                status=card.status,
                observed_at=card.observed_at,
                valid_from=card.valid_from,
                valid_to=card.valid_to,
                evidence_class=card.evidence_class,
                evidence_refs=card.evidence_refs,
                supersedes=card.supersedes,
                sensitivity=card.sensitivity,
                remote_allowed=card.remote_allowed,
                conditions=card.conditions,
                exceptions=card.exceptions,
                rationale=card.rationale,
                created_at=card.created_at,
                updated_at=card.updated_at,
                revision=card.revision,
                relative_path=card.relative_path,
                effective_status=eff_status,
            )
        resolved.append(card)

    return resolved


def get_semantic_profile(vault_root: Path, scope_project: str | None = None) -> SemanticProfile:
    """A2 önyüklemesi için aktif, geçerli kartlardan önceliklendirilmiş profil döner."""
    all_cards = scan_semantic_cards(vault_root)
    # Yalnızca efektif olarak aktif olanları filtrele
    active = [
        c for c in all_cards
        if c.effective_status == "active"
        and (c.valid_from is None or c.valid_from <= datetime.now(UTC))
        and (c.scope == "global" or (scope_project is not None and c.scope == "project" and c.scope_project == scope_project))
    ]

    corrections = [c for c in active if c.kind == "correction"]
    constraints = [c for c in active if c.kind == "constraint"]
    identity = [c for c in active if c.kind == "identity"]
    goals = [c for c in active if c.kind == "goal"]
    preferences = [c for c in active if c.kind == "preference"]

    return SemanticProfile(
        corrections=corrections[:3],
        constraints=constraints[:2],
        identity=identity[:2],
        goals=goals[:3],
        preferences=preferences[:4],
    )


def writable_root() -> Path:
    from app.integrations.obsidian.vault import require_writable_vault

    try:
        root, _ = require_writable_vault()
    except (RuntimeError, PermissionError) as exc:
        raise SemanticStorageError("VAULT_UNAVAILABLE", str(exc)) from exc
    return root


def readable_root() -> Path | None:
    from app.integrations.obsidian.vault import vault_context

    try:
        root, _ = vault_context()
        if root is None:
            return None
        resolved = root.resolve()
        if not resolved.is_dir() or not os.access(resolved, os.R_OK | os.X_OK):
            return None
        return resolved
    except (OSError, ValueError, PermissionError):
        return None
