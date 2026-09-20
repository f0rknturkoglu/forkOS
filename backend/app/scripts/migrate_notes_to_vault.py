"""forkOS Notes → Obsidian Vault migration CLI (PHASE 18, 25).

Varsayilan mod `--dry-run`dir: hicbir sey yazilmaz, yalnizca plan + metrik +
rapor uretilir. Kopyalama yalnizca `--apply` ile ve ancak preflight kapilari
temizse baslar.

    python -m app.scripts.migrate_notes_to_vault --dry-run
    python -m app.scripts.migrate_notes_to_vault --apply
    python -m app.scripts.migrate_notes_to_vault --verify

Cikis kodlari: 0 = temiz, 1 = blocker/hata, 2 = doğrulama tamamlanmadi.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from app.config import settings
from app.integrations.obsidian.migration.engine import (
    APPLY,
    DRY_RUN,
    VERIFY,
    MigrationOutcome,
    run_apply,
    run_dry_run,
    run_verify,
)

MODES = (DRY_RUN, APPLY, VERIFY)


def payload_of(outcome: MigrationOutcome) -> dict:
    metrics = outcome.metrics
    return {
        "mode": outcome.mode,
        "vault_root": outcome.vault_root,
        "vault_name": outcome.vault_name,
        "manifest_location": outcome.manifest_location,
        "blockers": outcome.blockers,
        "warnings": outcome.preflight.warnings,
        "checks": [
            {
                "name": check.name,
                "ok": check.ok,
                "detail": check.detail if not check.ok else "",
                "critical": check.critical,
            }
            for check in outcome.preflight.checks
        ],
        "source": {
            "total_notes": metrics.get("source_total_notes", 0),
            "active": metrics.get("source_active", 0),
            "archived": metrics.get("source_archived", 0),
            "trashed": metrics.get("source_trashed", 0),
            "personal": metrics.get("kind_personal", 0),
            "daily": metrics.get("kind_daily", 0),
            "project_journals": metrics.get("kind_project_journal", 0),
            "bookmark_notes": metrics.get("kind_bookmark_note", 0),
        },
        "result": {
            "copied": metrics.get("notes_copied", 0),
            "verified": metrics.get("notes_verified", 0),
            "already_migrated": metrics.get("notes_already_migrated", 0),
            "diverged": metrics.get("notes_diverged", 0),
            "failed": metrics.get("notes_failed", 0),
            "blocked": metrics.get("notes_blocked", 0),
            "planned": metrics.get("notes_planned", 0),
        },
        "attachments": {
            "count": metrics.get("attachment_count", 0),
            "bytes": metrics.get("attachment_bytes", 0),
            "copied": metrics.get("attachments_copied", 0),
            "reused": metrics.get("attachments_reused", 0),
            "failed": metrics.get("attachments_failed", 0),
        },
        "canvas": {
            "count": metrics.get("canvas_count", 0),
            "verified": metrics.get("canvas_verified", 0),
        },
        "wikilinks": {
            "rewritten": metrics.get("wikilinks_rewritten", 0),
            "unresolved": metrics.get("wikilinks_unresolved", 0),
        },
        "path_collisions": outcome.collisions,
        "source_fingerprint_before": outcome.fingerprint_before,
        "source_fingerprint_after": outcome.fingerprint_after,
        "ready_for_cutover": outcome.ready_for_cutover,
        "errors": outcome.errors,
    }


def print_summary(outcome: MigrationOutcome) -> None:
    metrics = outcome.metrics
    print(f"Mod: {outcome.mode} | Vault: {outcome.vault_root or 'yapılandırılmamış'}")
    print(f"Manifest: {outcome.manifest_location}")
    print(
        "Kaynak: {total} not (aktif {active}, arşiv {archived}, çöp {trashed}) | "
        "kişisel {personal}, günlük {daily}, proje günlüğü {journal}, yer imi {bookmark}".format(
            total=metrics.get("source_total_notes", 0),
            active=metrics.get("source_active", 0),
            archived=metrics.get("source_archived", 0),
            trashed=metrics.get("source_trashed", 0),
            personal=metrics.get("kind_personal", 0),
            daily=metrics.get("kind_daily", 0),
            journal=metrics.get("kind_project_journal", 0),
            bookmark=metrics.get("kind_bookmark_note", 0),
        )
    )
    print(
        "Sonuç: kopyalanan {copied}, doğrulanan {verified}, zaten aktarılmış {already}, "
        "diverged {diverged}, başarısız {failed}, bloke {blocked}, planlanan {planned}".format(
            copied=metrics.get("notes_copied", 0),
            verified=metrics.get("notes_verified", 0),
            already=metrics.get("notes_already_migrated", 0),
            diverged=metrics.get("notes_diverged", 0),
            failed=metrics.get("notes_failed", 0),
            blocked=metrics.get("notes_blocked", 0),
            planned=metrics.get("notes_planned", 0),
        )
    )
    print(
        "Ek: {count} ({size} bayt) | kopyalanan {copied}, yeniden kullanılan {reused}, "
        "başarısız {failed}".format(
            count=metrics.get("attachment_count", 0),
            size=metrics.get("attachment_bytes", 0),
            copied=metrics.get("attachments_copied", 0),
            reused=metrics.get("attachments_reused", 0),
            failed=metrics.get("attachments_failed", 0),
        )
    )
    print(
        "Canvas: {count} yan dosya (doğrulanan {verified}) | Wikilink: {rewritten} genişletildi, "
        "{unresolved} çözülemedi".format(
            count=metrics.get("canvas_count", 0),
            verified=metrics.get("canvas_verified", 0),
            rewritten=metrics.get("wikilinks_rewritten", 0),
            unresolved=metrics.get("wikilinks_unresolved", 0),
        )
    )
    print(f"Kaynak parmak izi: {outcome.fingerprint_before} -> {outcome.fingerprint_after}")

    if outcome.blockers:
        print("")
        print("KRİTİK BLOCKER:")
        for blocker in outcome.blockers:
            print(f"  - {blocker}")
    if outcome.preflight.warnings:
        print("")
        print("Uyarılar:")
        for warning in outcome.preflight.warnings:
            print(f"  - {warning}")
    if outcome.errors:
        print("")
        print(f"Hatalar: {len(outcome.errors)}")
        for error in outcome.errors[:10]:
            print(f"  - [{error.get('stage')}] {error.get('note_id') or '-'}: {error.get('error')}")

    print("")
    print(f"READY_FOR_CUTOVER = {'YES' if outcome.ready_for_cutover else 'NO'}")


async def main_async(mode: str, report_path: str | None, as_json: bool) -> int:
    vault_root = settings.resolved_obsidian_vault_path
    vault_name = settings.resolved_obsidian_vault_name

    if mode == DRY_RUN:
        outcome = await run_dry_run(vault_root, vault_name)
    elif mode == APPLY:
        outcome = await run_apply(vault_root, vault_name)
    else:
        outcome = await run_verify(vault_root, vault_name)

    if report_path:
        Path(report_path).write_text(outcome.report, encoding="utf-8")

    if as_json:
        print(json.dumps(payload_of(outcome), ensure_ascii=False, indent=2))
    else:
        print_summary(outcome)
        if report_path:
            print(f"\nRapor yazıldı: {report_path}")

    if outcome.blockers:
        return 2
    if mode in (APPLY, VERIFY) and not outcome.ready_for_cutover:
        return 1
    return 0


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="forkOS Notes → Obsidian Vault migration (varsayılan: --dry-run)"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true", help="plan + metrik (varsayılan, yazmaz)")
    group.add_argument("--apply", action="store_true", help="kopyala-ve-doğrula")
    group.add_argument("--verify", action="store_true", help="Vault'taki kopyaları doğrula")
    parser.add_argument("--report", default=None, help="Markdown raporunu bu yola yaz")
    parser.add_argument("--json", action="store_true", help="Makine okunur özet bas")
    args = parser.parse_args(argv)

    if args.apply:
        mode = APPLY
    elif args.verify:
        mode = VERIFY
    else:
        mode = DRY_RUN

    sys.exit(asyncio.run(main_async(mode, args.report, args.json)))


if __name__ == "__main__":
    main()
