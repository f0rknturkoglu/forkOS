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


class BookIn(BaseModel):
    title: str = Field(min_length=1)
    author: str | None = None
    status: str = "want"
    total_pages: int | None = None
    current_page: int = 0
    rating: int | None = Field(None, ge=1, le=5)
    notes: str | None = None


class BookPatch(BaseModel):
    title: str | None = None
    status: str | None = None
    current_page: int | None = None
    rating: int | None = Field(None, ge=1, le=5)
    notes: str | None = None
