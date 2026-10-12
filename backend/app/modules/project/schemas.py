from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ProjectIn(BaseModel):
    title: str = Field(min_length=1)
    status: str = "active"
    github_repo: str | None = None
    url: str | None = None
    stack: list[str] = []
    next_action: str | None = None
    position: int = 0


class ProjectPatch(BaseModel):
    title: str | None = None
    status: str | None = None
    github_repo: str | None = None
    url: str | None = None
    stack: list[str] | None = None
    next_action: str | None = None
    position: int | None = None


class MilestoneIn(BaseModel):
    title: str = Field(min_length=1)
    due_at: datetime | None = None
    position: int = 0


class MilestonePatch(BaseModel):
    title: str | None = None
    due_at: datetime | None = None
    completed: bool | None = None
    position: int | None = None


class TodoLinkIn(BaseModel):
    todo_id: uuid.UUID


class IssueToTodoIn(BaseModel):
    number: int = Field(ge=1)


class GithubCredentialsIn(BaseModel):
    login: str = Field(min_length=1)
    token: str = Field(min_length=1)


class ProjectResourceIn(BaseModel):
    client_uuid: uuid.UUID
    title: str = Field(min_length=1, max_length=300)
    url: str = Field(min_length=1, max_length=4000)

    @field_validator("title")
    @classmethod
    def resource_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Bağlantı adı gerekli")
        return value

    @field_validator("url")
    @classmethod
    def resource_url(cls, value: str) -> str:
        from urllib.parse import urlsplit

        value = value.strip()
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Geçerli, kimlik bilgisi içermeyen http(s) bağlantısı gerekli")
        return value


class ProjectResourceOut(BaseModel):
    id: uuid.UUID
    title: str
    url: str
