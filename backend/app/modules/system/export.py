from __future__ import annotations

import base64
import csv
import io
import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from html import escape
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import local_datetime, local_end_of_day, local_zone
from app.db import Base
from app.modules.system.secrets import is_secret_setting

ROOT_TABLES = ("entity", "link", "event")
BACKUP_EXCLUDED_TABLES = {"oauth_token"}  # erişim/yenileme tokenları yedeğe girmez


def backup_table_names() -> list[str]:
    """Metadata'daki her tabloyu açık bir secret denylist'i dışında kapsa."""
    available = set(Base.metadata.tables) - BACKUP_EXCLUDED_TABLES
    ordered = [table.name for table in Base.metadata.sorted_tables if table.name in available]
    return [*ROOT_TABLES, *(name for name in ordered if name not in ROOT_TABLES)]


def module_table_names() -> list[str]:
    return [name for name in backup_table_names() if name not in ROOT_TABLES]


def json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (UUID, Decimal)):
        return str(value)
    if isinstance(value, bytes):
        return value.hex()
    return value


async def rows(session: AsyncSession, table_name: str) -> list[dict]:
    table = Base.metadata.tables[table_name]
    result = (await session.execute(select(table))).mappings().all()
    return [{key: json_value(value) for key, value in row.items()} for row in result]


async def public_rows(session: AsyncSession, table_name: str) -> list[dict]:
    """`rows` + secret politikasi: `setting` satirlarinda secret key'ler
    payload'a HIC yazilmaz (bos/maskeli deger bile degil)."""
    values = await rows(session, table_name)
    if table_name != "setting":
        return values
    return [row for row in values if not is_secret_setting(str(row.get("key", "")))]


async def full_json(session: AsyncSession) -> dict:
    """Backup/export payload'i (v2).
    `manifest.row_counts`, payload'in kendisiyle dogrulanabilir butunluk
    kontroludur: yedek bozulmus ya da elle degistirilmisse import oncesi
    preflight bunu yakalar. v1 okuyucular icin `exported_at` koktepe korunur.
    """
    entities = await public_rows(session, "entity")
    links = await public_rows(session, "link")
    events = await public_rows(session, "event")
    modules = {
        name: await public_rows(session, name)
        for name in module_table_names()
    }
    exported_at = datetime.now(UTC).isoformat()

    # Yerel doküman dosyalarını (CV/PDF) yedeğe base64 olarak dahil et
    files: dict[str, dict[str, str]] = {}
    if "document" in modules:
        from app.modules.document.service import DOCUMENTS_DIR

        entity_titles = {e["id"]: e.get("title", "belge") for e in entities}
        for doc in modules["document"]:
            if doc.get("folder_id") == "local":
                doc_id = str(doc["id"])
                title = entity_titles.get(doc_id, "belge")
                doc_dir = DOCUMENTS_DIR / doc_id
                target = doc_dir / title
                if not target.exists() and doc_dir.exists():
                    for f in doc_dir.iterdir():
                        if f.is_file():
                            target = f
                            break
                if target.is_file():
                    try:
                        content = target.read_bytes()
                        files[doc_id] = {
                            "filename": target.name,
                            "data_b64": base64.b64encode(content).decode("ascii"),
                        }
                    except OSError:
                        pass

    return {
        "version": 2,
        "exported_at": exported_at,
        "manifest": {
            "app": "forkos",
            "exported_at": exported_at,
            "row_counts": {
                "entities": len(entities),
                "links": len(links),
                "events": len(events),
                "modules": {name: len(rows) for name, rows in modules.items()},
            },
        },
        "entities": entities,
        "links": links,
        "events": events,
        "modules": modules,
        "files": files,
    }


async def csv_export(session: AsyncSession, module: str) -> str:
    if module not in module_table_names():
        raise ValueError("desteklenmeyen export modülü")
    values = await public_rows(session, module)
    output = io.StringIO()
    fieldnames = list(Base.metadata.tables[module].columns.keys())
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in values:
        writer.writerow(
            {
                key: json.dumps(value, ensure_ascii=False)
                if isinstance(value, (dict, list))
                else value
                for key, value in row.items()
            }
        )
    return output.getvalue()


async def markdown_export(session: AsyncSession) -> str:
    lines = ["# forkOS Export", ""]
    # p.notes 0029'da note tablosuna tasindi; proje notlarini oradan topla.
    project_rows = (
        await session.execute(
            text("""select e.title, p.status, p.next_action,
                           (select string_agg(n.body, E'\\n\\n---\\n\\n'
                                              order by n.journal_day nulls last, e2.created_at)
                            from note n join entity e2 on e2.id = n.id
                            where n.project_id = p.id and n.body <> '') as notes
                    from project p join entity e on e.id=p.id order by p.position""")
        )
    ).mappings()
    lines.extend(["## Projects", ""])
    for item in project_rows:
        lines.extend(
            [
                f"### {item['title']}",
                "",
                f"- Status: {item['status']}",
                f"- Next: {item['next_action'] or '—'}",
                "",
                item["notes"] or "",
                "",
            ]
        )
    review_rows = (
        await session.execute(
            text("""select e.title, r.note from review r join entity e on e.id=r.id
                    where r.note is not null order by r.period_start desc""")
        )
    ).mappings()
    lines.extend(["## Reviews", ""])
    for item in review_rows:
        lines.extend([f"### {item['title']}", "", item["note"], ""])

    # Standalone / serbest notlar
    note_rows = (
        await session.execute(
            text("""select e.title, n.body, n.journal_day, e.created_at
                    from note n join entity e on e.id = n.id
                    where n.project_id is null and (n.body <> '' or e.title <> '')
                    order by n.journal_day desc nulls last, e.created_at desc""")
        )
    ).mappings()
    if note_rows:
        lines.extend(["## Notes", ""])
        for item in note_rows:
            header = item["title"] or (f"Günlük {item['journal_day']}" if item["journal_day"] else "Not")
            date_val = item["journal_day"] or (item["created_at"].strftime("%Y-%m-%d") if item["created_at"] else "")
            lines.extend([f"### {header}", ""])
            if date_val:
                lines.extend([f"- Tarih: {date_val}", ""])
            if item["body"]:
                lines.extend([item["body"], ""])

    # Görevler (Todo)
    todo_rows = (
        await session.execute(
            text("""select e.title, t.status, t.priority, t.due_at, t.completed_at
                    from todo t join entity e on e.id = t.id
                    order by case when t.status = 'open' then 0 else 1 end, t.priority desc, t.due_at nulls last""")
        )
    ).mappings()
    if todo_rows:
        lines.extend(["## Tasks", ""])
        for item in todo_rows:
            box = "[x]" if item["status"] == "done" else "[ ]"
            meta_parts = [f"P{item['priority']}"]
            if item["due_at"]:
                meta_parts.append(f"Due: {item['due_at'].strftime('%Y-%m-%d')}")
            if item["completed_at"]:
                meta_parts.append(f"Done: {item['completed_at'].strftime('%Y-%m-%d')}")
            meta_str = f" ({', '.join(meta_parts)})" if meta_parts else ""
            lines.append(f"- {box} {item['title']}{meta_str}")
        lines.append("")

    # Öğrenme (Courses & Resources)
    course_rows = (
        await session.execute(
            text("""select e.title, c.platform, c.status
                    from course c join entity e on e.id = c.id
                    order by c.status, e.title""")
        )
    ).mappings()
    resource_rows = (
        await session.execute(
            text("""select e.title, lr.url, lr.kind, lr.completed_at
                    from learning_resource lr join entity e on e.id = lr.id
                    order by case when lr.completed_at is null then 0 else 1 end, e.title""")
        )
    ).mappings()
    if course_rows or resource_rows:
        lines.extend(["## Learning", ""])
        if course_rows:
            lines.extend(["### Courses", ""])
            for c in course_rows:
                lines.append(f"- **{c['title']}** ({c['platform'] or 'Genel'}) — *{c['status']}*")
            lines.append("")
        if resource_rows:
            lines.extend(["### Resources", ""])
            for r in resource_rows:
                state = "tamamlandı" if r["completed_at"] else "devam ediyor"
                url_part = f"({r['url']}) " if r["url"] else ""
                lines.append(f"- **{r['title']}** {url_part}({r['kind']}) — *{state}*")
            lines.append("")

    return "\n".join(lines)


async def bookmarks_html(session: AsyncSession) -> str:
    values = (
        await session.execute(
            text("""select e.title, b.url, b.saved_at from bookmark b join entity e on e.id=b.id
                    order by b.collection, b.saved_at desc""")
        )
    ).mappings()
    items = "\n".join(
        f'<DT><A HREF="{escape(row["url"], quote=True)}" '
        f'ADD_DATE="{int(row["saved_at"].timestamp())}">{escape(row["title"])}</A>'
        for row in values
    )
    return (
        '<!DOCTYPE NETSCAPE-Bookmark-file-1>\n<META HTTP-EQUIV="Content-Type" '
        'CONTENT="text/html; charset=UTF-8">\n<TITLE>forkOS Bookmarks</TITLE>\n'
        f"<H1>forkOS Bookmarks</H1>\n<DL><p>\n{items}\n</DL><p>\n"
    )


async def opml(session: AsyncSession) -> str:
    values = (
        await session.execute(
            text(
                "select e.title, f.url, f.site_url from feed f "
                "join entity e on e.id=f.id where f.active"
            )
        )
    ).mappings()
    outlines = "\n".join(
        f'<outline text="{escape(row["title"], quote=True)}" '
        f'title="{escape(row["title"], quote=True)}" type="rss" '
        f'xmlUrl="{escape(row["url"], quote=True)}" '
        f'htmlUrl="{escape(row["site_url"] or "", quote=True)}"/>'
        for row in values
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?><opml version="2.0">'
        f"<head><title>forkOS Feeds</title></head><body>{outlines}</body></opml>"
    )


def ics_datetime(value: datetime | date) -> str:
    """ICS zaman damgasi; ciplak `date` yerel gun sonuna yerlestirilir."""
    if not isinstance(value, datetime):
        value = local_end_of_day(value)
    elif value.tzinfo is None:
        value = value.replace(tzinfo=local_zone())
    return value.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


async def ics(session: AsyncSession) -> str:
    from app.core.deadlines import collect_deadlines

    deadline_rows = await collect_deadlines(session, limit=2000)
    slots = (
        await session.execute(
            text("""select p.id, e.title, p.day, p.start_min, p.duration_min
                    from plan_slot p join entity e on e.id=p.entity_id""")
        )
    ).mappings()
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//forkOS//EN"]
    for row in deadline_rows:
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:deadline-{row['entity_id']}@forkos",
                f"DTSTART:{ics_datetime(row['due_at'])}",
                f"SUMMARY:{row['title']}",
                "END:VEVENT",
            ]
        )
    for row in slots:
        minute = row["start_min"] or 0
        start = local_datetime(row["day"], minute)
        end = start + timedelta(minutes=row["duration_min"] or 30)
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:plan-{row['id']}@forkos",
                f"DTSTART:{ics_datetime(start)}",
                f"DTEND:{ics_datetime(end)}",
                f"SUMMARY:{row['title']}",
                "END:VEVENT",
            ]
        )
    return "\r\n".join([*lines, "END:VCALENDAR", ""])
