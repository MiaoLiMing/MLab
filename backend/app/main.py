from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import text

from app.api.v1 import (
    assistants,
    auth,
    conversations,
    documents,
    files,
    memories,
    model_settings,
    resources,
    search,
    tasks,
    tools,
    users,
)
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.rate_limit import rate_limiter
from app.db.seed import seed_system_data
from app.db.session import SessionFactory, create_database_tables

settings = get_settings()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("mlab")


@asynccontextmanager
async def lifespan(_: FastAPI):
    if not settings.is_production:
        await create_database_tables()
    settings.local_storage_path.mkdir(parents=True, exist_ok=True)
    async with SessionFactory() as db:
        await seed_system_data(db)
    if settings.is_production:
        rate_limiter.enable_redis(settings.redis_url)
    try:
        yield
    finally:
        await rate_limiter.close()


app = FastAPI(
    title=f"{settings.app_name} API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or str(uuid4())
    request.state.request_id = request_id
    path = request.url.path
    forwarded_for = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    client = forwarded_for or (request.client.host if request.client else "unknown")
    limit = 10 if path in {"/api/v1/auth/login", "/api/v1/auth/register"} else 0
    if path.endswith("/messages"):
        limit = 30
    elif path == "/api/v1/files":
        limit = 20
    if limit and not await rate_limiter.allow(f"{client}:{request.method}:{path}", limit):
        return JSONResponse(
            status_code=429,
            headers={"Retry-After": "60", "x-request-id": request_id},
            content={
                "error": {
                    "code": "RATE_LIMITED",
                    "message": "请求过于频繁，请稍后重试",
                    "request_id": request_id,
                    "details": None,
                }
            },
        )
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    return response


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "request_id": request.state.request_id,
                "details": exc.details,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "请求参数不正确",
                "request_id": request.state.request_id,
                "details": exc.errors(),
            }
        },
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled request error", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "服务暂时不可用",
                "request_id": request.state.request_id,
                "details": None,
            }
        },
    )


@app.get("/health/live", tags=["health"])
async def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
async def ready() -> dict[str, str]:
    async with SessionFactory() as db:
        await db.execute(text("SELECT 1"))
    if settings.is_production:
        redis = Redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=1)
        try:
            await redis.ping()
        finally:
            await redis.aclose()
    return {"status": "ready"}


for router in (
    auth.router,
    users.router,
    model_settings.router,
    conversations.router,
    assistants.router,
    tools.router,
    tasks.router,
    documents.router,
    resources.router,
    memories.router,
    files.router,
    search.router,
):
    app.include_router(router, prefix="/api/v1")
