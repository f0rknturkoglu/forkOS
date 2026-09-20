"""Notes -> Obsidian Vault Migration Dry-Run Planner.

Bu script veritabaninda veya Vault'ta HICBIR SEY DEGISTIRMEZ (zero mutation).
Mevcut forkOS notlarini inceler, hedef Vault yapisindaki yollari simule eder,
cakismalari ve ozel durumlari (canvas, ekler, cop kutusu) raporlar.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Entity
from app.core.refs import WIKILINK
from app.db import SessionLocal
from app.integrations.obsidian.security import sanitize_filename
from app.modules.note.models import Note, NoteAttachment, NoteFolder
from app.modules.project.models import Project


async def plan_notes_migration(session: AsyncSession) -> dict[str, Any]:
    """Mevcut notlari analiz eder ve ayrintili bir migration plani cikarir."""
    # 1. Proje basliklarini haritala
    project_rows = (
        await session.execute(
            select(Project.id, Entity.title).join(Entity, Entity.id == Project.id)
        )
    ).all()
    project_titles: dict[uuid.UUID, str] = {row[0]: row[1] for row in project_rows}

    # 2. Klasor basliklarini haritala
    folder_rows = (
        await session.execute(
            select(NoteFolder.id, Entity.title, NoteFolder.parent_id).join(
                Entity, Entity.id == NoteFolder.id
            )
        )
    ).all()
    folder_titles: dict[uuid.UUID, str] = {row[0]: row[1] for row in folder_rows}

    # 3. Not ek sayilarini haritala
    att_counts_raw = (
        await session.execute(
            select(NoteAttachment.note_id, func.count(NoteAttachment.id)).group_by(
                NoteAttachment.note_id
            )
        )
    ).all()
    attachment_counts: dict[uuid.UUID, int] = {row[0]: row[1] for row in att_counts_raw}

    # 4. Tum notlari cek
    notes_raw = (
        await session.execute(
            select(Note, Entity.title, Entity.archived_at)
            .join(Entity, Entity.id == Note.id)
            .order_by(Note.journal_day.asc().nullslast(), Note.id.asc())
        )
    ).all()

    total_notes = len(notes_raw)
    personal_notes = 0
    daily_notes = 0
    project_journals = 0
    archived_notes = 0
    trashed_notes = 0
    notes_with_canvas = 0
    notes_with_attachments = 0
    notes_with_wikilinks = 0
    total_attachment_files = sum(attachment_counts.values())

    path_assignments: dict[str, list[uuid.UUID]] = {}
    plan_items: list[dict[str, Any]] = []

    for note, title, archived_at in notes_raw:
        is_archived = archived_at is not None
        is_trashed = note.trashed_at is not None
        has_canvas = bool(note.canvas_state and isinstance(note.canvas_state, dict))
        att_count = attachment_counts.get(note.id, 0) + len(note.attachments or [])
        has_wikilinks = bool(WIKILINK.search(note.body or ""))

        if is_archived:
            archived_notes += 1
        if is_trashed:
            trashed_notes += 1
        if has_canvas:
            notes_with_canvas += 1
        if att_count > 0:
            notes_with_attachments += 1
        if has_wikilinks:
            notes_with_wikilinks += 1

        warnings: list[str] = []
        if is_trashed:
            warnings.append("Not çöp kutusunda")
        if is_archived:
            warnings.append("Not arşivlenmiş")
        if has_canvas:
            warnings.append("Excalidraw canvas çizimi içeriyor (özel eklenti gerektirir)")

        # Hedef yol hesaplama
        if note.journal_day and not note.project_id:
            daily_notes += 1
            forkos_type = "note"
            target_path = f"10 Daily/{note.journal_day.isoformat()}.md"
        elif note.journal_day and note.project_id:
            project_journals += 1
            forkos_type = "project"
            p_name = sanitize_filename(project_titles.get(note.project_id, "Project"))
            target_path = f"20 Projects/{p_name}/Journal/{note.journal_day.isoformat()}.md"
        else:
            personal_notes += 1
            forkos_type = "note"
            safe_title = sanitize_filename(title or "Untitled")
            folder_part = ""
            if note.folder_id and note.folder_id in folder_titles:
                folder_part = f"{sanitize_filename(folder_titles[note.folder_id])}/"
            target_path = f"00 Inbox/Imported/{folder_part}{safe_title}.md"

        path_assignments.setdefault(target_path, []).append(note.id)

        plan_items.append(
            {
                "note_id": str(note.id),
                "title": title,
                "target_path": target_path,
                "forkos_type": forkos_type,
                "attachments_count": att_count,
                "has_canvas": has_canvas,
                "has_wikilinks": has_wikilinks,
                "project_id": str(note.project_id) if note.project_id else None,
                "warnings": warnings,
            }
        )

    # Hedef dosya adı çakışmalarını tespit et
    collisions = {
        path: [str(nid) for nid in nids]
        for path, nids in path_assignments.items()
        if len(nids) > 1
    }

    metrics = {
        "total_notes": total_notes,
        "personal_notes": personal_notes,
        "daily_notes": daily_notes,
        "project_journals": project_journals,
        "archived_notes": archived_notes,
        "trashed_notes": trashed_notes,
        "notes_with_canvas": notes_with_canvas,
        "notes_with_attachments": notes_with_attachments,
        "total_attachment_files": total_attachment_files,
        "notes_with_wikilinks": notes_with_wikilinks,
        "potential_filename_collisions": len(collisions),
    }

    return {
        "metrics": metrics,
        "collisions": collisions,
        "plan": plan_items,
    }


def format_markdown_report(result: dict[str, Any]) -> str:
    """Sonucları okunabilir Markdown raporuna dönüştürür."""
    m = result["metrics"]
    lines = [
        "# forkOS Notes -> Obsidian Vault Migration Dry-Run Report",
        "",
        "> [!NOTE]",
        "> Bu rapor salt-okunur (dry-run) simülasyondur. Veritabanında veya Vault'ta hiçbir değişiklik yapılmamıştır.",
        "",
        "## 1. Özet Metrikler",
        "",
        "| Metrik | Değer |",
        "|---|---|",
        f"| Toplam Not Sayısı | {m['total_notes']} |",
        f"| Kişisel Serbest Notlar | {m['personal_notes']} |",
        f"| Günlük Yazılar (Daily) | {m['daily_notes']} |",
        f"| Proje Günlükleri | {m['project_journals']} |",
        f"| Arşivdeki Notlar | {m['archived_notes']} |",
        f"| Çöp Kutusundaki Notlar | {m['trashed_notes']} |",
        f"| Canvas İçeren Notlar | {m['notes_with_canvas']} |",
        f"| Ekli Notlar | {m['notes_with_attachments']} |",
        f"| Toplam Fiziksel Ek Dosyası | {m['total_attachment_files']} |",
        f"| Wikilink `[[...]]` İçeren Notlar | {m['notes_with_wikilinks']} |",
        f"| Potansiyel Dosya Adı Çakışması | {m['potential_filename_collisions']} |",
        "",
    ]

    collisions = result.get("collisions", {})
    if collisions:
        lines.append("## 2. Olası Dosya Adı Çakışmaları (Collisions)")
        lines.append("")
        for path, nids in collisions.items():
            lines.append(f"- **`{path}`**: {len(nids)} adet not bu yolla çakışıyor ({', '.join(nids[:3])}...)")
        lines.append("")
        lines.append("*(Gerçek aktarım sırasında çakışan dosyalara `(1)`, `(2)` biçiminde deterministik sonek verilecektir.)*")
        lines.append("")

    lines.append("## 3. İlk 20 Notun Simüle Edilen Hedef Yolları")
    lines.append("")
    lines.append("| Not Başlığı | Hedef Yol | Tür | Ekler | Uyarılar |")
    lines.append("|---|---|---|---|---|")
    for item in result.get("plan", [])[:20]:
        warns = ", ".join(item["warnings"]) if item["warnings"] else "-"
        lines.append(
            f"| {item['title'][:30]} | `{item['target_path']}` | {item['forkos_type']} | {item['attachments_count']} | {warns} |"
        )

    return "\n".join(lines)


async def main_async(format_type: str, output_path: str | None) -> int:
    async with SessionLocal() as session:
        result = await plan_notes_migration(session)

    if format_type == "json":
        text = json.dumps(result, ensure_ascii=False, indent=2)
    else:
        text = format_markdown_report(result)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write(text)
        print(f"Rapor yazıldı: {output_path}")
    else:
        print(text)

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="forkOS Notes -> Vault Migration Dry-Run Planner")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Çıktı formatı")
    parser.add_argument("--output", "-o", default=None, help="Dosyaya kaydetmek için yol")
    args = parser.parse_args()

    sys.exit(asyncio.run(main_async(args.format, args.output)))


if __name__ == "__main__":
    main()
