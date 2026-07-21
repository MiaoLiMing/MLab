from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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
    await create_database_tables()
    settings.local_storage_path.mkdir(parents=True, exist_ok=True)
    async with SessionFactory() as db:
        await seed_system_data(db)
    yield


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
