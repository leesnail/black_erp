# -*- coding: utf-8 -*-
"""FastAPI 应用入口"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1 import api_router
from app.core.config import settings
from app.core.database import Base, engine
from app.core.exceptions import register_exception_handlers
from app.core.logging import new_trace_id, setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    # 开发环境自动建表（生产用 Alembic）
    if settings.is_dev:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        from app.seed import run_seed

        await run_seed()
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.is_dev else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    tid = new_trace_id()
    response = await call_next(request)
    response.headers["X-Trace-Id"] = tid
    return response


# 上传静态（发票附件等，开发直链；生产走鉴权代理）
app.mount("/data/uploads", StaticFiles(directory=str(settings.upload_path)), name="uploads")

app.include_router(api_router)
register_exception_handlers(app)


@app.get("/health")
async def health():
    return {"ok": True, "env": settings.app_env}
