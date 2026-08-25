from __future__ import annotations

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

from app.core.time import local_datetime
from app.db import Base

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


async def full_json(session: AsyncSession) -> dict:
    return {
        "version": 1,
        "exported_at": datetime.now(UTC).isoformat(),
        "entities": await rows(session, "entity"),
        "links": await rows(session, "link"),
        "events": await rows(session, "event"),
        "modules": {
            name: await rows(session, name)
            for name in module_table_names()
        },
    }


async def csv_export(session: AsyncSession, module: str) -> str:
    if module not in module_table_names():
        raise ValueError("desteklenmeyen export modülü")
    values = await rows(session, module)
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
    project_rows = (
        await session.execute(
            text("""select e.title, p.status, p.next_action, p.notes
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


def ics_datetime(value: datetime) -> str:
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
