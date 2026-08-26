from pydantic import BaseModel, Field


class CourseIn(BaseModel):
    title: str = Field(min_length=1)
    platform: str | None = None
    url: str | None = None
    status: str = "planned"
    progress_pct: int = Field(0, ge=0, le=100)
    notes: str | None = None


class CoursePatch(BaseModel):
    title: str | None = None
    status: str | None = None
    progress_pct: int | None = Field(None, ge=0, le=100)
    notes: str | None = None
