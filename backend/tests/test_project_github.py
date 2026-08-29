from __future__ import annotations

import importlib
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.db import engine
from app.main import app

project_router = importlib.import_module("app.modules.project.router")


async def _database_ready() -> bool:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("select 1 from project limit 1"))
        return True
    except Exception:
        return False


@pytest.fixture
async def client():
    if not await _database_ready():
        pytest.skip("Postgres yok veya migration calismamis")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


def _panel() -> dict:
    return {
        "repo": "owner/repo",
        "url": "https://github.com/owner/repo",
        "description": None,
        "stars": 0,
        "forks": 0,
        "watchers": 0,
        "language": "Python",
        "open_issues": 2,
        "default_branch": "main",
        "pushed_at": "2026-08-29T10:00:00Z",
        "fetched_at": "2026-08-29T10:01:00Z",
        "private": True,
        "issues": [
            {
                "number": number,
                "title": title,
                "url": f"https://github.com/owner/repo/issues/{number}",
                "state": "open",
                "labels": [],
                "assignee": None,
                "comments": 0,
                "created_at": "2026-08-29T09:00:00Z",
                "updated_at": "2026-08-29T10:00:00Z",
                "author": "owner",
                "draft": False,
            }
            for number, title in ((17, "Fix sync"), (18, "Improve panel"))
        ],
        "pulls": [],
        "commits": [],
        "authenticated": True,
    }


async def test_project_github_marks_issues_already_converted_to_todos(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = (
        await client.post(
            "/api/projects",
            json={"title": f"GitHub {uuid.uuid4().hex[:8]}", "github_repo": "owner/repo"},
        )
    ).json()
    todo = (
        await client.post(
            "/api/todos",
            json={"title": "owner/repo#17 Fix sync", "project_id": project["id"]},
        )
    ).json()

    async def fake_overview(*_args, **_kwargs):
        return _panel()

    async def fake_issue(*_args, **_kwargs):
        return {
            "number": 17,
            "title": "Fix sync",
            "url": "https://github.com/owner/repo/issues/17",
            "labels": [],
            "body": "",
        }

    monkeypatch.setattr(project_router.github_repo, "overview", fake_overview)
    monkeypatch.setattr(project_router.github_repo, "issue", fake_issue)

    response = await client.get(f"/api/projects/{project['id']}/github")

    assert response.status_code == 200
    issues = {item["number"]: item for item in response.json()["issues"]}
    assert issues[17]["todo_id"] == todo["id"]
    assert issues[18]["todo_id"] is None

    duplicate = await client.post(
        f"/api/projects/{project['id']}/github/issues", json={"number": 17}
    )
    assert duplicate.status_code == 201
    assert duplicate.json()["duplicate"] is True
    linked = (await client.get(f"/api/projects/{project['id']}/todos")).json()
    assert [item["id"] for item in linked].count(todo["id"]) == 1
