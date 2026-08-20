from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.links import link
from app.db import get_session
from app.integrations.models import OAuthToken
from app.modules.project import github, service
from app.modules.project.models import GithubActivity, Milestone, Project
from app.modules.project.schemas import (
    GithubCredentialsIn,
    MilestoneIn,
    MilestonePatch,
    ProjectIn,
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
    item = await session.get(Milestone, milestone_id)
    if item is None:
        raise HTTPException(404)
    await session.delete(item)
    await session.commit()


@router.get("/projects/{project_id}/todos")
async def project_todos(project_id: uuid.UUID, session: AsyncSession = Depends(get_session)):
    return await service.project_todos(session, project_id)


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


@router.post("/github/sync")
async def sync_github(session: AsyncSession = Depends(get_session)):
    try:
        return {"synced": await github.sync(session)}
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get("/github/activity")
async def github_activity(session: AsyncSession = Depends(get_session)):
    return list(
        (
            await session.execute(
                select(GithubActivity).order_by(GithubActivity.day.desc()).limit(730)
            )
        ).scalars()
    )
