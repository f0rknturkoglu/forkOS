"""Migration orkestrasyonu: preflight, dry-run, apply, verify ve rapor (PHASE 18-23).

Kopyalama SALT OKUNUR kaynaktan yapilir; hedef yalnizca Vault'tur.
`--dry-run` Vault'a HICBIR SEY yazmaz (manifest ve rapor dahil).
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import text

from app.integrations.obsidian.migration import manifest as manifest_mod
from app.integrations.obsidian.migration.manifest import (
    BLOCKED,
    COPIED,
    DIVERGED,
    FAILED,
    PLANNED,
    SKIPPED_EXISTING,
    VERIFIED,
    Manifest,
    ManifestIncompatible,
    NoteEntry,
)
from app.integrations.obsidian.migration.plan import (
    MigrationPlan,
    PlannedAttachment,
    PlannedNote,
    build_plan,
    collect_vault_paths,
    sha256_of,
)
from app.integrations.obsidian.migration.render import build_body, build_frontmatter, render_note
from app.integrations.obsidian.migration.source import (
    SourceSnapshot,
    load_snapshot,
    read_only_session,
)
from app.integrations.obsidian.migration.verify import (
    ExpectedNote,
    canvas_canonical_sha,
    verify_note,
    verify_plan_identity,
)
from app.integrations.obsidian.migration.writer import (
    CREATED,
    REUSED,
    canonical_json,
    write_attachment,
    write_canvas_sidecar,
    write_note,
)
from app.integrations.obsidian.migration.writer import (
    DIVERGED as WRITE_DIVERGED,
)
from app.integrations.obsidian.service import refresh_vault_index, vault_index
from app.modules.note import storage as attachment_storage

DRY_RUN = "dry-run"
APPLY = "apply"
VERIFY = "verify"


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""
    critical: bool = True


@dataclass
class PreflightReport:
    checks: list[Check] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.blockers

    @property
    def blockers(self) -> list[str]:
        return [
            f"{check.name}: {check.detail}" if check.detail else check.name
            for check in self.checks
            if not check.ok and check.critical
        ]

    @property
    def warnings(self) -> list[str]:
        return [
            f"{check.name}: {check.detail}" if check.detail else check.name
            for check in self.checks
            if not check.ok and not check.critical
        ]


@dataclass
class VaultState:
    configured: bool
    available: bool
    readable: bool
    writable: bool
    managed_by_id: dict[str, str] = field(default_factory=dict)
    paths: set[str] = field(default_factory=set)
    conflicts: dict[str, list[str]] = field(default_factory=dict)
    invalid_files: list[str] = field(default_factory=list)
    diagnostic: str | None = None


@dataclass
class MigrationOutcome:
    mode: str
    vault_root: str | None
    vault_name: str
    preflight: PreflightReport
    manifest: Manifest | None
    metrics: dict
    collisions: dict[str, list[str]]
    fingerprint_before: str | None
    fingerprint_after: str | None
    ready_for_cutover: bool
    blockers: list[str]
    errors: list[dict]
    report: str = ""

    @property
    def manifest_location(self) -> str:
        if not self.vault_root:
            return "yok (Vault yapılandırılmamış)"
        return str(Path(self.vault_root) / manifest_mod.MANIFEST_DIR)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _ordered(plan: MigrationPlan) -> list[uuid.UUID]:
    return sorted(plan.notes, key=str)


def read_vault_state(vault_root: Path | None, vault_name: str) -> VaultState:
    """Vault durumu: managed indeks + tum dosya yollari (gizli dizinler haric)."""
    if vault_root is None:
        return VaultState(False, False, False, False, diagnostic="Vault yapılandırılmamış")
    status = refresh_vault_index(vault_root, vault_name)
    managed = {item.forkos_id: item.relative_path for item in vault_index.items.values()}
    paths = collect_vault_paths(vault_root) if status.readable else set()
    return VaultState(
        configured=True,
        available=status.available,
        readable=status.readable,
        writable=status.writable,
        managed_by_id=managed,
        paths=paths,
        conflicts=dict(vault_index.conflicts),
        invalid_files=list(status.invalid_files),
        diagnostic=status.diagnostic,
    )


async def _source_db_reachable() -> tuple[bool, str]:
    try:
        async with read_only_session() as session:
            await session.execute(text("select 1"))
        return True, ""
    except Exception as exc:  # noqa: BLE001 - preflight raporlanir
        return False, str(exc)


def _attachment_storage_check(snapshot: SourceSnapshot | None) -> tuple[bool, str]:
    needs_blobs = any(
        attachment.generation == "blob"
        for note in (snapshot.notes if snapshot else ())
        for attachment in note.attachments
    )
    directory = attachment_storage.ATTACHMENTS_DIR
    if not needs_blobs:
        return True, "blob gerektiren ek yok"
    if not directory.is_dir():
        return False, f"ek deposu bulunamadı: {directory}"
    if not os.access(directory, os.R_OK):
        return False, f"ek deposu okunamıyor: {directory}"
    return True, ""


async def run_preflight(
    vault_root: Path | None,
    vault_name: str,
    *,
    plan: MigrationPlan | None = None,
    state: VaultState | None = None,
    snapshot: SourceSnapshot | None = None,
) -> PreflightReport:
    """PHASE 19 kapilari. Kritik blocker varsa apply HIC baslamaz."""
    vault = state or read_vault_state(vault_root, vault_name)
    # Bagimli kontroller yalnizca Vault yapilandirilmissa anlamlidir: aksi
    # halde tek bir blocker yerine dort gurultulu satir cikardi.
    configured = vault.configured
    checks = [
        Check("vault_configured", configured, "OBSIDIAN_VAULT_PATH boş"),
        Check(
            "vault_available",
            vault.available or not configured,
            vault.diagnostic or "Vault erişilebilir değil",
        ),
        Check(
            "vault_readable",
            vault.readable or not configured,
            "Vault dizini okunamıyor",
        ),
        Check(
            "vault_writable",
            vault.writable or not configured,
            "Vault dizinine yazma izni yok",
        ),
        Check(
            "vault_identity_conflicts",
            not vault.conflicts,
            f"{len(vault.conflicts)} duplicate forkos_id: {sorted(vault.conflicts)[:3]}",
        ),
        Check(
            "vault_managed_metadata",
            not vault.invalid_files,
            f"{len(vault.invalid_files)} geçersiz metadata: {vault.invalid_files[:2]}",
        ),
    ]

    reachable, detail = await _source_db_reachable()
    checks.append(Check("source_db", reachable, detail))

    storage_ok, storage_detail = _attachment_storage_check(snapshot)
    checks.append(Check("attachment_storage", storage_ok, storage_detail, critical=False))

    try:
        existing = manifest_mod.load_manifest(vault_root) if vault_root else None
        checks.append(
            Check(
                "manifest_version",
                True,
                f"mevcut manifest sürüm {existing.manifest_version}"
                if existing
                else "mevcut manifest yok",
                critical=False,
            )
        )
    except ManifestIncompatible as exc:
        checks.append(Check("manifest_version", False, str(exc)))

    if plan is not None:
        identity_errors = verify_plan_identity(plan)
        checks.append(Check("plan_identity", not identity_errors, "; ".join(identity_errors[:3])))
        checks.append(Check("plan_blockers", not plan.blocked, "; ".join(plan.blocked[:3])))

    return PreflightReport(checks=checks)


async def load_migration_inputs(
    vault_root: Path | None, vault_name: str
) -> tuple[SourceSnapshot, VaultState, MigrationPlan]:
    """Kaynak snapshot + Vault durumu + tam plan (Vault'a yazmaz)."""
    state = read_vault_state(vault_root, vault_name)
    async with read_only_session() as session:
        snapshot = await load_snapshot(session)
    plan = build_plan(
        snapshot, existing_paths=state.paths, managed_by_id=state.managed_by_id
    )
    return snapshot, state, plan


def _reference_paths(plan: MigrationPlan) -> dict[str, str]:
    return {
        attachment_id: planned.vault_path
        for attachment_id, planned in plan.attachments.items()
    }


def expected_note(
    plan: MigrationPlan,
    planned: PlannedNote,
    *,
    migrated_at: str | None,
) -> ExpectedNote:
    """Kaynaktan beklenen ciktiyi yeniden uret (dogrulama da bunu kullanir)."""
    note = planned.note
    bookmark = (
        plan.snapshot.bookmarks.get(note.source_bookmark_id)
        if note.source_bookmark_id
        else None
    )
    frontmatter = build_frontmatter(
        note,
        planned.kind,
        migrated_at=migrated_at or _now(),
        bookmark=bookmark,
        canvas_sidecar=planned.canvas_sidecar_path,
    )
    body_result = build_body(
        note,
        attachment_paths={
            attachment_id: planned.vault_path
            for attachment_id, planned in plan.attachments.items()
            if planned.note_id == note.note_id
        },
        reference_paths=_reference_paths(plan),
        resolution=plan.snapshot.title_resolution,
        note_paths={nid: entry.target_path for nid, entry in plan.notes.items()},
        stem_index=plan.stem_index,
    )
    return ExpectedNote(
        frontmatter=frontmatter,
        body=body_result.body,
        content=render_note(frontmatter, body_result.body),
        migrated_at=migrated_at,
        canvas_canonical_sha=canvas_canonical_sha(note.canvas_state) if note.has_canvas else None,
        attachments=[
            plan.attachments[attachment_id]
            for attachment_id in planned.attachment_paths
            if attachment_id in plan.attachments
        ],
        wikilinks=body_result.wikilinks,
    )


def _attachment_payload(planned: PlannedAttachment, status: str) -> dict:
    return {
        "attachment_id": planned.attachment_id,
        "original_name": planned.original_name,
        "vault_path": planned.vault_path,
        "sha256": planned.content_sha256,
        "size": len(planned.content) if planned.content is not None else planned.size,
        "storage": planned.generation,
        "status": status,
        "error": planned.error,
    }


def _new_manifest(vault_root: Path, vault_name: str, fingerprint: str) -> Manifest:
    now = _now()
    return Manifest(
        vault_root=str(vault_root),
        vault_name=vault_name,
        generated_at=now,
        updated_at=now,
        source_fingerprint_before=fingerprint,
    )


def plan_manifest_entries(plan: MigrationPlan, manifest: Manifest) -> None:
    """Plan asamasini manifest'e yaz: her not `planned` olarak gorunur (PHASE 7/20)."""
    for note_id in _ordered(plan):
        planned = plan.notes[note_id]
        key = str(note_id)
        entry = manifest.notes.get(key)
        if entry is None:
            entry = NoteEntry(
                note_id=key,
                title=planned.note.title,
                note_kind=planned.kind,
                target_path=planned.target_path,
                base_path=planned.base_path,
                status=PLANNED,
                source_body_sha256=planned.note.body_sha256,
                collision=planned.collision,
                warnings=list(planned.warnings),
            )
            manifest.notes[key] = entry
        entry.note_kind = planned.kind
        entry.target_path = planned.target_path
        entry.base_path = planned.base_path
        entry.title = planned.note.title
        entry.collision = planned.collision
        entry.errors = []
        entry.attachments = [
            _attachment_payload(plan.attachments[attachment_id], PLANNED)
            for attachment_id in planned.attachment_paths
            if attachment_id in plan.attachments
        ]
        entry.canvas = (
            {
                "sidecar_path": planned.canvas_sidecar_path,
                "canonical_sha256": canvas_canonical_sha(planned.note.canvas_state),
                "size": len(canonical_json(planned.note.canvas_state).encode("utf-8")),
                "status": PLANNED,
                "error": None,
            }
            if planned.canvas_sidecar_path
            else None
        )


def _metrics(manifest: Manifest, plan: MigrationPlan) -> dict:
    statuses = {status: 0 for status in manifest_mod.ALL_STATUSES}
    kinds = {"personal": 0, "daily": 0, "project_journal": 0, "bookmark_note": 0}
    states = {"active": 0, "archived": 0, "trashed": 0}
    for note in plan.snapshot.notes:
        states[note.state] = states.get(note.state, 0) + 1

    attachments_copied = attachments_reused = attachments_failed = 0
    attachment_bytes = 0
    canvas_count = canvas_written = 0
    wikilinks_rewritten = wikilinks_unresolved = 0
    created_this_run = 0

    for entry in manifest.notes.values():
        statuses[entry.status] = statuses.get(entry.status, 0) + 1
        kinds[entry.note_kind] = kinds.get(entry.note_kind, 0) + 1
        if entry.created_this_run:
            created_this_run += 1
        for attachment in entry.attachments:
            attachment_bytes += int(attachment.get("size") or 0)
            if attachment.get("status") == CREATED:
                attachments_copied += 1
            elif attachment.get("status") == REUSED:
                attachments_reused += 1
            elif attachment.get("status") == WRITE_DIVERGED:
                attachments_failed += 1
        if entry.canvas:
            canvas_count += 1
            if entry.canvas.get("status") in (CREATED, REUSED):
                canvas_written += 1
        wikilinks_rewritten += int(entry.wikilinks.get("rewritten") or 0)
        wikilinks_unresolved += len(entry.wikilinks.get("unresolved") or [])

    return {
        "source_total_notes": len(plan.snapshot.notes),
        "source_active": states["active"],
        "source_archived": states["archived"],
        "source_trashed": states["trashed"],
        "kind_personal": kinds["personal"],
        "kind_daily": kinds["daily"],
        "kind_project_journal": kinds["project_journal"],
        "kind_bookmark_note": kinds["bookmark_note"],
        "statuses": statuses,
        "notes_copied": created_this_run,
        "notes_verified": statuses.get(VERIFIED, 0) + statuses.get(SKIPPED_EXISTING, 0),
        "notes_already_migrated": statuses.get(SKIPPED_EXISTING, 0),
        "notes_diverged": statuses.get(DIVERGED, 0),
        "notes_failed": statuses.get(FAILED, 0),
        "notes_blocked": statuses.get(BLOCKED, 0),
        "notes_planned": statuses.get(PLANNED, 0),
        "notes_copied_pending_verify": statuses.get(COPIED, 0),
        "attachment_count": sum(len(entry.attachments) for entry in manifest.notes.values()),
        "attachment_bytes": attachment_bytes,
        "attachments_copied": attachments_copied,
        "attachments_reused": attachments_reused,
        "attachments_failed": attachments_failed,
        "canvas_count": canvas_count,
        "canvas_verified": canvas_written,
        "wikilinks_rewritten": wikilinks_rewritten,
        "wikilinks_unresolved": wikilinks_unresolved,
        "path_collisions": len(plan.path_collisions),
    }


def _ready_for_cutover(
    mode: str,
    metrics: dict,
    manifest: Manifest,
    preflight: PreflightReport,
    errors: list[dict],
) -> bool:
    if mode not in (APPLY, VERIFY):
        return False
    if preflight.blockers or errors:
        return False
    if metrics["notes_verified"] != metrics["source_total_notes"]:
        return False
    if metrics["notes_diverged"] or metrics["notes_failed"] or metrics["notes_blocked"]:
        return False
    if metrics["attachments_failed"] or metrics["canvas_count"] != metrics["canvas_verified"]:
        return False
    return manifest.source_fingerprint_before == manifest.source_fingerprint_after


def _outcome(
    mode: str,
    vault_root: Path | None,
    vault_name: str,
    preflight: PreflightReport,
    manifest: Manifest,
    plan: MigrationPlan,
    *,
    fingerprint_after: str | None,
    errors: list[dict],
    blockers: list[str],
) -> MigrationOutcome:
    metrics = _metrics(manifest, plan)
    outcome = MigrationOutcome(
        mode=mode,
        vault_root=str(vault_root) if vault_root else None,
        vault_name=vault_name,
        preflight=preflight,
        manifest=manifest,
        metrics=metrics,
        collisions=plan.path_collisions,
        fingerprint_before=manifest.source_fingerprint_before,
        fingerprint_after=fingerprint_after,
        ready_for_cutover=_ready_for_cutover(mode, metrics, manifest, preflight, errors),
        blockers=blockers,
        errors=errors,
    )
    outcome.report = render_report(outcome)
    return outcome


async def run_dry_run(vault_root: Path | None, vault_name: str) -> MigrationOutcome:
    """Tam plan + metrik + rapor; Vault'a HICBIR SEY yazilmaz."""
    snapshot, state, plan = await load_migration_inputs(vault_root, vault_name)
    preflight = await run_preflight(
        vault_root, vault_name, plan=plan, state=state, snapshot=snapshot
    )
    manifest = Manifest(
        vault_root=str(vault_root) if vault_root else "",
        vault_name=vault_name,
        generated_at=_now(),
        updated_at=_now(),
        source_fingerprint_before=snapshot.fingerprint,
    )
    plan_manifest_entries(plan, manifest)
    return _outcome(
        DRY_RUN,
        vault_root,
        vault_name,
        preflight,
        manifest,
        plan,
        fingerprint_after=snapshot.fingerprint,
        errors=[],
        blockers=preflight.blockers,
    )


def _attachment_pass(
    vault_root: Path,
    plan: MigrationPlan,
    manifest: Manifest,
    errors: list[dict],
) -> None:
    """Tum ekleri kopyala (notlardan ONCE): govde baglantilari nihai yolu tasir."""
    statuses: dict[str, str] = {}
    for note_id in _ordered(plan):
        planned_note = plan.notes[note_id]
        entry = manifest.notes[str(note_id)]
        for attachment_id in planned_note.attachment_paths:
            planned = plan.attachments.get(attachment_id)
            if planned is None:
                continue
            source = next(
                (
                    item
                    for item in planned_note.note.attachments
                    if item.attachment_id == attachment_id
                ),
                None,
            )
            if source is None:
                statuses[attachment_id] = PLANNED
                continue
            vault_path, status, digest, error = write_attachment(vault_root, planned, source)
            planned.vault_path = vault_path
            if digest:
                planned.content_sha256 = digest
            statuses[attachment_id] = status
            if error:
                entry.errors.append(f"{planned.original_name}: {error}")
                errors.append(
                    {
                        "stage": "attachment",
                        "note_id": str(note_id),
                        "error": f"{planned.original_name}: {error}",
                    }
                )
        entry.attachments = [
            _attachment_payload(plan.attachments[aid], statuses.get(aid, PLANNED))
            for aid in planned_note.attachment_paths
            if aid in plan.attachments
        ]


def _canvas_pass(
    vault_root: Path,
    plan: MigrationPlan,
    manifest: Manifest,
    errors: list[dict],
) -> None:
    for note_id in _ordered(plan):
        planned = plan.notes[note_id]
        entry = manifest.notes[str(note_id)]
        if not planned.canvas_sidecar_path:
            continue
        status, canonical_sha, error = write_canvas_sidecar(
            vault_root, planned.canvas_sidecar_path, planned.note.canvas_state
        )
        entry.canvas = {
            "sidecar_path": planned.canvas_sidecar_path,
            "canonical_sha256": canonical_sha,
            "size": len(canonical_json(planned.note.canvas_state).encode("utf-8")),
            "status": status,
            "error": error,
        }
        if error:
            entry.errors.append(f"canvas: {error}")
            errors.append({"stage": "canvas", "note_id": str(note_id), "error": error})


def _note_pass(
    vault_root: Path,
    plan: MigrationPlan,
    manifest: Manifest,
    errors: list[dict],
) -> None:
    """Her notu yaz/dogrula ve manifest'i not basina atomik guncelle."""
    for note_id in _ordered(plan):
        planned = plan.notes[note_id]
        key = str(note_id)
        entry = manifest.notes[key]
        migrated_at = entry.migrated_at or _now()
        expected = expected_note(plan, planned, migrated_at=migrated_at)

        status, existing = write_note(vault_root, planned.target_path, expected.content)
        entry.created_this_run = status == CREATED

        if status == REUSED and existing:
            adopted = _migrated_at_of(existing)
            if adopted and adopted != migrated_at:
                migrated_at = adopted
                expected = expected_note(plan, planned, migrated_at=migrated_at)

        problems = verify_note(vault_root, planned, expected)
        entry.migrated_at = migrated_at
        entry.migrated_body_sha256 = sha256_of(expected.body.strip().encode("utf-8"))
        entry.wikilinks = {
            "rewritten": expected.wikilinks.rewritten,
            "retained": expected.wikilinks.retained,
            "unresolved": expected.wikilinks.unresolved,
            "non_note": expected.wikilinks.non_note,
        }
        entry.errors = [*entry.errors, *problems]

        if problems:
            entry.status = DIVERGED if status == WRITE_DIVERGED else FAILED
            for problem in problems:
                errors.append({"stage": "note", "note_id": key, "error": problem})
        else:
            if status == CREATED:
                entry.status = VERIFIED
            elif status == REUSED:
                entry.status = SKIPPED_EXISTING
            else:  # pragma: no cover - REUSED/DIVERGED disinda durum yok
                entry.status = FAILED

        manifest_mod.save_manifest(vault_root, manifest)


def _migrated_at_of(content: str) -> str | None:
    from app.integrations.obsidian.frontmatter import parse_frontmatter

    metadata, _body = parse_frontmatter(content)
    value = (metadata or {}).get("forkos_migrated_at")
    return str(value) if value else None


def _index_pass(
    vault_root: Path,
    vault_name: str,
    plan: MigrationPlan,
    manifest: Manifest,
    errors: list[dict],
) -> None:
    """Vault indeksini tazele ve kimliklerin tek cozumlendigini dogrula (PHASE 21)."""
    status = refresh_vault_index(vault_root, vault_name)
    if status.invalid_files:
        errors.append(
            {
                "stage": "index",
                "note_id": None,
                "error": f"{len(status.invalid_files)} geçersiz metadata: {status.invalid_files[:2]}",
            }
        )
    for note_id, entry in manifest.notes.items():
        if entry.status not in (VERIFIED, SKIPPED_EXISTING):
            continue
        if vault_index.is_conflicted(note_id):
            errors.append(
                {
                    "stage": "index",
                    "note_id": note_id,
                    "error": f"forkos_id çakışması: {vault_index.conflicts.get(note_id)}",
                }
            )
            continue
        item = vault_index.get_item(note_id)
        if item is None:
            errors.append(
                {"stage": "index", "note_id": note_id, "error": "Vault indeksinde bulunamadı"}
            )
        elif item.relative_path != entry.target_path:
            errors.append(
                {
                    "stage": "index",
                    "note_id": note_id,
                    "error": f"indeks yolu farklı: {item.relative_path} != {entry.target_path}",
                }
            )


async def run_apply(vault_root: Path | None, vault_name: str) -> MigrationOutcome:
    """KOPYALAMA: kaynaktan Vault'a not, ek ve canvas yan dosyasi yazar."""
    snapshot, state, plan = await load_migration_inputs(vault_root, vault_name)
    preflight = await run_preflight(
        vault_root, vault_name, plan=plan, state=state, snapshot=snapshot
    )

    existing_manifest: Manifest | None = None
    if vault_root is not None:
        try:
            existing_manifest = manifest_mod.load_manifest(vault_root)
        except ManifestIncompatible as exc:
            preflight.checks.append(Check("manifest_version", False, str(exc)))

    manifest = existing_manifest or _new_manifest(
        vault_root or Path(), vault_name, snapshot.fingerprint
    )
    manifest.source_fingerprint_before = manifest.source_fingerprint_before or snapshot.fingerprint
    manifest.updated_at = _now()
    plan_manifest_entries(plan, manifest)

    errors: list[dict] = []
    if not preflight.ok or vault_root is None:
        return _outcome(
            APPLY,
            vault_root,
            vault_name,
            preflight,
            manifest,
            plan,
            fingerprint_after=None,
            errors=errors,
            blockers=preflight.blockers,
        )

    manifest_mod.save_manifest(vault_root, manifest)
    _attachment_pass(vault_root, plan, manifest, errors)
    _canvas_pass(vault_root, plan, manifest, errors)
    _note_pass(vault_root, plan, manifest, errors)
    _index_pass(vault_root, vault_name, plan, manifest, errors)

    async with read_only_session() as session:
        after = await load_snapshot(session)
    manifest.source_fingerprint_after = after.fingerprint
    manifest.updated_at = _now()
    manifest_mod.save_manifest(vault_root, manifest)

    outcome = _outcome(
        APPLY,
        vault_root,
        vault_name,
        preflight,
        manifest,
        plan,
        fingerprint_after=manifest.source_fingerprint_after,
        errors=errors,
        blockers=preflight.blockers,
    )
    _persist_report(vault_root, outcome, errors)
    return outcome


async def run_verify(vault_root: Path | None, vault_name: str) -> MigrationOutcome:
    """Vault'taki kopyalari kaynakla anlamsal olarak dogrula (yazmaz)."""
    snapshot, state, plan = await load_migration_inputs(vault_root, vault_name)
    preflight = await run_preflight(
        vault_root, vault_name, plan=plan, state=state, snapshot=snapshot
    )
    errors: list[dict] = []

    manifest: Manifest | None = None
    if vault_root is not None:
        try:
            manifest = manifest_mod.load_manifest(vault_root)
        except ManifestIncompatible as exc:
            preflight.checks.append(Check("manifest_version", False, str(exc)))

    if manifest is None:
        preflight.checks.append(
            Check("manifest_exists", False, "Manifest bulunamadı; önce --apply çalıştırın")
        )
        manifest = _new_manifest(vault_root or Path(), vault_name, snapshot.fingerprint)
        plan_manifest_entries(plan, manifest)

    for note_id in _ordered(plan):
        planned = plan.notes[note_id]
        key = str(note_id)
        entry = manifest.notes.get(key)
        if entry is None:
            errors.append(
                {"stage": "verify", "note_id": key, "error": "Manifest'te not yok"}
            )
            continue
        entry.target_path = planned.target_path
        _recover_attachment_paths(entry, plan)
        expected = expected_note(plan, planned, migrated_at=entry.migrated_at)
        problems = verify_note(vault_root, planned, expected) if vault_root else ["Vault yok"]
        entry.errors = problems
        if problems:
            entry.status = FAILED
            for problem in problems:
                errors.append({"stage": "verify", "note_id": key, "error": problem})
        elif entry.status not in (VERIFIED, SKIPPED_EXISTING):
            entry.status = VERIFIED
        if vault_root is not None:
            manifest_mod.save_manifest(vault_root, manifest)

    if vault_root is not None:
        _index_pass(vault_root, vault_name, plan, manifest, errors)
        manifest.updated_at = _now()
        manifest_mod.save_manifest(vault_root, manifest)

    outcome = _outcome(
        VERIFY,
        vault_root,
        vault_name,
        preflight,
        manifest,
        plan,
        fingerprint_after=snapshot.fingerprint,
        errors=errors,
        blockers=preflight.blockers,
    )
    if vault_root is not None:
        _persist_report(vault_root, outcome, errors)
    return outcome


def _recover_attachment_paths(entry: NoteEntry, plan: MigrationPlan) -> None:
    """Manifest'teki nihai ek yollarini plan'a geri yaz (dogrulama ayni yolu okusun)."""
    for attachment in entry.attachments:
        attachment_id = str(attachment.get("attachment_id"))
        vault_path = attachment.get("vault_path")
        target = plan.attachments.get(attachment_id)
        if target is not None and vault_path and target.vault_path != vault_path:
            target.vault_path = str(vault_path)


def _persist_report(vault_root: Path, outcome: MigrationOutcome, errors: list[dict]) -> None:
    manifest_mod.write_report(vault_root, outcome.report)
    manifest_mod.write_errors(
        vault_root,
        {
            "generated_at": _now(),
            "ready_for_cutover": outcome.ready_for_cutover,
            "blockers": outcome.blockers,
            "errors": errors,
        },
    )


def render_report(outcome: MigrationOutcome) -> str:
    """PHASE 22 global rapor."""
    m = outcome.metrics
    lines = [
        "# forkOS Notes → Obsidian Vault Migration Report",
        "",
        f"- Mod: `{outcome.mode}`",
        f"- Vault: `{outcome.vault_root or 'yapılandırılmamış'}`",
        f"- Manifest: `{outcome.manifest_location}`",
        "",
        "## Kaynak",
        "",
        f"- Toplam not: {m.get('source_total_notes', 0)}",
        f"- Aktif: {m.get('source_active', 0)} | Arşiv: {m.get('source_archived', 0)} | "
        f"Çöp: {m.get('source_trashed', 0)}",
        f"- Kişisel: {m.get('kind_personal', 0)} | Günlük: {m.get('kind_daily', 0)} | "
        f"Proje günlüğü: {m.get('kind_project_journal', 0)} | "
        f"Yer imi notu: {m.get('kind_bookmark_note', 0)}",
        "",
        "## Sonuç",
        "",
        f"- Doğrulanan not: {m.get('notes_verified', 0)}",
        f"- Bu turda kopyalanan: {m.get('notes_copied', 0)}",
        f"- Zaten aktarılmış (yeniden kullanıldı): {m.get('notes_already_migrated', 0)}",
        f"- Diverged (elle değişmiş ya da kaynak değişmiş): {m.get('notes_diverged', 0)}",
        f"- Başarısız: {m.get('notes_failed', 0)}",
        f"- Bloke: {m.get('notes_blocked', 0)}",
        f"- Planlanan (henüz yazılmadı): {m.get('notes_planned', 0)}",
        "",
        "## Ekler ve Canvas",
        "",
        f"- Ek sayısı: {m.get('attachment_count', 0)} ({m.get('attachment_bytes', 0)} bayt)",
        f"- Kopyalanan: {m.get('attachments_copied', 0)} | Yeniden kullanılan: "
        f"{m.get('attachments_reused', 0)} | Başarısız: {m.get('attachments_failed', 0)}",
        f"- Canvas yan dosyası: {m.get('canvas_count', 0)} "
        f"(yazılan/doğrulanan: {m.get('canvas_verified', 0)})",
        "",
        "## Wikilink",
        "",
        f"- Yola genişletilen: {m.get('wikilinks_rewritten', 0)}",
        f"- Çözülemeyen (korunan): {m.get('wikilinks_unresolved', 0)}",
        "",
        "## Çakışma ve Kimlik",
        "",
        f"- Deterministik çözülen taban yol çakışması: {m.get('path_collisions', 0)}",
        f"- Kritik blocker: {len(outcome.blockers)}",
        "",
        "## Kaynak Parmak İzi",
        "",
        f"- SOURCE_FINGERPRINT_BEFORE: `{outcome.fingerprint_before}`",
        f"- SOURCE_FINGERPRINT_AFTER: `{outcome.fingerprint_after}`",
        "",
    ]
    if outcome.collisions:
        lines.append("### Çakışan taban yollar")
        lines.append("")
        for path, ids in sorted(outcome.collisions.items()):
            lines.append(f"- `{path}`: {len(ids)} not → deterministik id soneki")
        lines.append("")

    if outcome.blockers:
        lines.append("## Blockerlar")
        lines.append("")
        lines.extend(f"- {blocker}" for blocker in outcome.blockers)
        lines.append("")

    if outcome.errors:
        lines.append("## Hatalar")
        lines.append("")
        for error in outcome.errors[:50]:
            lines.append(
                f"- [{error.get('stage')}] {error.get('note_id') or '-'}: {error.get('error')}"
            )
        if len(outcome.errors) > 50:
            lines.append(f"- … toplam {len(outcome.errors)} hata")
        lines.append("")

    lines.append("## Karar")
    lines.append("")
    lines.append(f"READY_FOR_CUTOVER = {'YES' if outcome.ready_for_cutover else 'NO'}")
    lines.append("")
    return "\n".join(lines)
