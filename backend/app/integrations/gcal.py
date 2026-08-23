from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx

from app.core.time import local_datetime

BASE_URL = "https://www.googleapis.com/calendar/v3"


def parse_google_time(value: dict[str, str]) -> tuple[datetime, bool]:
    if "dateTime" in value:
        return datetime.fromisoformat(value["dateTime"].replace("Z", "+00:00")), False
    return local_datetime(date.fromisoformat(value["date"])).astimezone(UTC), True


async def list_events(
    token: str,
    *,
    sync_token: str | None = None,
    time_min: datetime | None = None,
) -> tuple[list[dict[str, Any]], str | None]:
    params: dict[str, str] = {"singleEvents": "true", "maxResults": "2500"}
    if sync_token:
        params["syncToken"] = sync_token
    else:
        since = time_min or datetime.now(UTC) - timedelta(days=90)
        params["timeMin"] = since.isoformat().replace("+00:00", "Z")

    items: list[dict[str, Any]] = []
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            response = await client.get(
                f"{BASE_URL}/calendars/primary/events", params=params, headers=headers
            )
            response.raise_for_status()
            data = response.json()
            items.extend(data.get("items", []))
            page_token = data.get("nextPageToken")
            if not page_token:
                return items, data.get("nextSyncToken")
            params["pageToken"] = page_token


async def upsert_event(
    token: str, event: dict[str, Any], google_event_id: str | None
) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=30) as client:
        if google_event_id:
            response = await client.patch(
                f"{BASE_URL}/calendars/primary/events/{google_event_id}",
                json=event,
                headers=headers,
            )
        else:
            response = await client.post(
                f"{BASE_URL}/calendars/primary/events", json=event, headers=headers
            )
        response.raise_for_status()
        return response.json()
