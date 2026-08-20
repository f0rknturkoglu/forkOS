from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.router import router as core_router
from app.modules import MODULES


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Life OS", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(core_router, prefix="/api")

# Her modul kendi router'ini registry uzerinden verir -- main.py'yi duzenlemene gerek yok
for module in MODULES:
    app.include_router(module.router, prefix="/api")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "modules": [m.id for m in MODULES]}
