from __future__ import annotations

import uuid
from datetime import date

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.links import link
from app.core.time import local_today
from app.db import get_session
from app.integrations.models import OAuthToken
from app.modules.project import github_repo, service
from app.modules.project.models import Project
from app.modules.project.schemas import (
    GithubCredentialsIn,
    IssueToTodoIn,
    MilestoneIn,
    MilestonePatch,
    ProjectIn,
    ProjectJournalNoteIn,
    ProjectPatch,
    TodoLinkIn,
)

router = APIRouter(tags=["projects"])


@router.get("/projects")
async def projects(status: str | None = None, session: AsyncSession = Depends(get_session)):
    return await service.list_projects(session, status)


@router.post("/projects", status_code=201)
async def add_project(body: ProjectIn, session: AsyncSession = Depends(get_session)):
    return await service.create(session, body)


@router.patch("/projects/{project_id}")
async def patch_project(
    project_id: uuid.UUID, body: ProjectPatch, session: AsyncSession = Depends(get_session)
):
    result = await service.patch(session, project_id, body)
    if result is None:
        raise HTTPException(404)
    return result


@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(project_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    """Projeyi siler.

    Kilometre taslari ve link'ler cascade ile gider; PROJEYE BAGLI GOREVLER
    KALIR -- is bitmedigi icin projenin kapanmasi gorevleri yok etmemeli.
    """
    if not await service.delete(session, project_id):
        raise HTTPException(404)


@router.post("/projects/{project_id}/milestones", status_code=201)
async def add_milestone(
    project_id: uuid.UUID, body: MilestoneIn, session: AsyncSession = Depends(get_session)
):
    result = await service.add_milestone(session, project_id, body)
    if result is None:
        raise HTTPException(404)
    return result


@router.patch("/milestones/{milestone_id}")
async def patch_milestone(
    milestone_id: uuid.UUID,
    body: MilestonePatch,
    session: AsyncSession = Depends(get_session),
):
    result = await service.patch_milestone(session, milestone_id, body)
    if result is None:
        raise HTTPException(404)
    return result


@router.delete("/milestones/{milestone_id}", status_code=204)
async def delete_milestone(milestone_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    if not await service.delete_milestone(session, milestone_id):
        raise HTTPException(404)


@router.get("/projects/{project_id}/todos")
async def project_todos(project_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    return await service.project_todos(session, project_id)


@router.get("/projects/{project_id}/journal")
async def project_journal(
    project_id: uuid.UUID,
    limit: int = 60,
    session: AsyncSession = Depends(get_session),
):
    if await session.get(Project, project_id) is None:
        raise HTTPException(404)
    return await service.journal(session, project_id, limit)


@router.put("/projects/{project_id}/journal/{day}")
async def put_project_journal_note(
    project_id: uuid.UUID,
    day: date,
    body: ProjectJournalNoteIn,
    session: AsyncSession = Depends(get_session),
):
    if await session.get(Project, project_id) is None:
        raise HTTPException(404)
    if day > local_today():
        raise HTTPException(400, "Gelecek bir gun icin gunluk notu yazilamaz")
    return await service.upsert_journal_note(session, project_id, day, body.body)


@router.post("/projects/{project_id}/todos", status_code=201)
async def add_project_todo(
    project_id: uuid.UUID, body: TodoLinkIn, session: AsyncSession = Depends(get_session)
):
    if await session.get(Project, project_id) is None:
        raise HTTPException(404)
    await link(session, body.todo_id, project_id, "belongs_to")
    await session.commit()
    return {"ok": True}


@router.post("/auth/github")
async def github_credentials(
    body: GithubCredentialsIn, session: AsyncSession = Depends(get_session)
):
    token = await session.get(OAuthToken, "github")
    if token is None:
        token = OAuthToken(provider="github", access_token=body.token)
        session.add(token)
    token.access_token = body.token
    token.scopes = body.login
    await session.commit()
    return {"connected": True, "login": body.login}


@router.get("/auth/github/status")
async def github_status(session: AsyncSession = Depends(get_session)):
    token = await session.get(OAuthToken, "github")
    return {"connected": token is not None, "login": token.scopes if token else None}


def _github_error(exc: httpx.HTTPStatusError) -> str:
    """GitHub'in kendi aciklamasini yuzeye cikar (404 mu, limit mi, yetki mi)."""
    try:
        detail = exc.response.json().get("message", "")
    except ValueError:
        detail = exc.response.text[:200]
    if exc.response.status_code == 403 and "rate limit" in detail.lower():
        detail += (" — Ayarlar'dan GitHub kişisel token'ı bağlarsan"
                   " limit 60/saatten 5000/saate çıkar.")
    return f"GitHub {exc.response.status_code}: {detail}"


async def _github_token(session: AsyncSession) -> str | None:
    row = await session.get(OAuthToken, "github")
    return row.access_token if row else None


@router.get("/projects/{project_id}/github")
async def project_github(
    project_id: uuid.UUID,
    refresh: bool = False,
    session: AsyncSession = Depends(get_session),
):
    """Projeye bagli deponun paneli: ozet, acik issue/PR, son commit'ler."""
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(404)
    if not project.github_repo:
        raise HTTPException(400, "Bu projeye bagli bir GitHub deposu yok")
    try:
        panel = await github_repo.overview(
            project.github_repo, await _github_token(session), refresh=refresh
        )
        todo_ids = await service.github_issue_todo_ids(
            session, project, [item["number"] for item in panel["issues"]]
        )
        return {
            **panel,
            "issues": [
                {**item, "todo_id": todo_ids.get(item["number"])}
                for item in panel["issues"]
            ],
        }
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, _github_error(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"GitHub'a ulasilamadi: {exc}") from exc


@router.post("/projects/{project_id}/github/issues", status_code=201)
async def issue_to_todo(
    project_id: uuid.UUID,
    body: IssueToTodoIn,
    session: AsyncSession = Depends(get_session),
):
    """GitHub issue'sunu gorev yapar ve projeye baglar.

    Ayni issue ikinci kez gonderilirse yeni gorev acilmaz -- mevcut gorev
    doner. Boylece "gorev olustur" dugmesine iki kez basmak sorun degil.
    """
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(404)
    if not project.github_repo:
        raise HTTPException(400, "Bu projeye bagli bir GitHub deposu yok")

    try:
        detail = await github_repo.issue(
            project.github_repo, body.number, await _github_token(session)
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, _github_error(exc)) from exc

    return await service.todo_from_issue(session, project, detail)
