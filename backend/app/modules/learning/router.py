from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.modules.learning import service
from app.modules.learning.models import Book, Course
from app.modules.learning.schemas import BookIn, BookPatch, CourseIn, CoursePatch

router = APIRouter(tags=["learning"])


@router.get("/courses")
async def courses(s: AsyncSession = Depends(get_session)):
    return await service.list_items(s, Course)


@router.post("/courses", status_code=201)
async def add_course(b: CourseIn, s: AsyncSession = Depends(get_session)):
    return await service.create_item(s, Course, b)


@router.patch("/courses/{id}")
async def patch_course(id: UUID, b: CoursePatch, s: AsyncSession = Depends(get_session)):
    r = await service.patch_item(s, Course, id, b)
    if not r:
        raise HTTPException(404)
    return r


@router.get("/books")
async def books(s: AsyncSession = Depends(get_session)):
    return await service.list_items(s, Book)


@router.post("/books", status_code=201)
async def add_book(b: BookIn, s: AsyncSession = Depends(get_session)):
    return await service.create_item(s, Book, b)


@router.patch("/books/{id}")
async def patch_book(id: UUID, b: BookPatch, s: AsyncSession = Depends(get_session)):
    r = await service.patch_item(s, Book, id, b)
    if not r:
        raise HTTPException(404)
    return r


@router.get("/learning/queue")
async def queue(kind: str | None = None, s: AsyncSession = Depends(get_session)):
    return await service.queue(s, kind)


@router.delete("/courses/{id}", status_code=204)
async def delete_course(id: UUID, session: AsyncSession = Depends(get_session)):
    if not await service.delete_item(session, Course, id):
        raise HTTPException(404)


@router.delete("/books/{id}", status_code=204)
async def delete_book(id: UUID, session: AsyncSession = Depends(get_session)):
    if not await service.delete_item(session, Book, id):
        raise HTTPException(404)
