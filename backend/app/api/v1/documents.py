from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Response, status
from sqlalchemy import select

from app.api.deps import AppSettings, CurrentUser, DBSession
from app.core.errors import AppError, NotFoundError
from app.models.entities import Document, DocumentVersion
from app.schemas.content import (
    AIActionRequest,
    AITextResponse,
    DocumentCreate,
    DocumentResponse,
    DocumentUpdate,
    DocumentVersionResponse,
)
from app.services.completion import complete_text

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentResponse])
async def list_documents(user: CurrentUser, db: DBSession) -> list[Document]:
    return list(
        await db.scalars(
            select(Document)
            .where(Document.user_id == user.id, Document.is_archived.is_(False))
            .order_by(Document.updated_at.desc())
        )
    )


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(payload: DocumentCreate, user: CurrentUser, db: DBSession) -> Document:
    document = Document(user_id=user.id, **payload.model_dump())
    db.add(document)
    await db.flush()
    db.add(
        DocumentVersion(
            document_id=document.id,
            version=1,
            snapshot=payload.model_dump(mode="json"),
            created_at=datetime.now(UTC),
        )
    )
    await db.commit()
    await db.refresh(document)
    return document


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: UUID, user: CurrentUser, db: DBSession) -> Document:
    document = await db.scalar(
        select(Document).where(Document.id == document_id, Document.user_id == user.id)
    )
    if document is None:
        raise NotFoundError("文稿")
    return document


@router.patch("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: UUID, payload: DocumentUpdate, user: CurrentUser, db: DBSession
) -> Document:
    document = await db.scalar(
        select(Document).where(Document.id == document_id, Document.user_id == user.id)
    )
    if document is None:
        raise NotFoundError("文稿")
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(document, field, value)
    if "content_json" in changes or "content_text" in changes:
        document.current_version += 1
        db.add(
            DocumentVersion(
                document_id=document.id,
                version=document.current_version,
                snapshot={
                    "title": document.title,
                    "content_json": document.content_json,
                    "content_text": document.content_text,
                },
                created_at=datetime.now(UTC),
            )
        )
    await db.commit()
    await db.refresh(document)
    return document


@router.get("/{document_id}/versions", response_model=list[DocumentVersionResponse])
async def list_document_versions(
    document_id: UUID, user: CurrentUser, db: DBSession
) -> list[DocumentVersion]:
    document = await db.scalar(
        select(Document.id).where(Document.id == document_id, Document.user_id == user.id)
    )
    if document is None:
        raise NotFoundError("文稿")
    return list(
        await db.scalars(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.version.desc())
        )
    )


@router.post("/{document_id}/versions/{version}/restore", response_model=DocumentResponse)
async def restore_document_version(
    document_id: UUID, version: int, user: CurrentUser, db: DBSession
) -> Document:
    document = await db.scalar(
        select(Document).where(Document.id == document_id, Document.user_id == user.id)
    )
    if document is None:
        raise NotFoundError("文稿")
    snapshot = await db.scalar(
        select(DocumentVersion).where(
            DocumentVersion.document_id == document_id, DocumentVersion.version == version
        )
    )
    if snapshot is None:
        raise NotFoundError("文稿版本")
    document.title = str(snapshot.snapshot.get("title") or document.title)
    document.content_json = snapshot.snapshot.get("content_json") or {}
    document.content_text = str(snapshot.snapshot.get("content_text") or "")
    document.current_version += 1
    db.add(
        DocumentVersion(
            document_id=document.id,
            version=document.current_version,
            snapshot={
                "title": document.title,
                "content_json": document.content_json,
                "content_text": document.content_text,
            },
            created_at=datetime.now(UTC),
        )
    )
    await db.commit()
    await db.refresh(document)
    return document


@router.post("/{document_id}/ai-actions", response_model=AITextResponse)
async def document_ai_action(
    document_id: UUID,
    payload: AIActionRequest,
    user: CurrentUser,
    db: DBSession,
    settings: AppSettings,
) -> AITextResponse:
    document = await db.scalar(
        select(Document).where(Document.id == document_id, Document.user_id == user.id)
    )
    if document is None:
        raise NotFoundError("文稿")
    source = (payload.selected_text or document.content_text).strip()
    if not source:
        raise AppError("EMPTY_DOCUMENT", "请先填写文稿内容", 422)
    instructions = {
        "rewrite": "在不改变事实的前提下提升清晰度、结构和表达，直接输出改写结果。",
        "continue": "延续原文语气和逻辑继续写作，直接输出续写部分。",
        "summarize": "提炼核心观点、结论和行动项，直接输出结构化摘要。",
    }
    prompt = (
        f"任务：{instructions[payload.action]}\n"
        f"附加要求：{payload.instruction or '无'}\n\n原文：\n{source}"
    )
    content = await complete_text(
        db,
        settings,
        user.id,
        prompt,
        system_prompt="你是严谨的中文写作助手，不编造原文中不存在的事实。",
    )
    return AITextResponse(content=content)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: UUID, user: CurrentUser, db: DBSession) -> Response:
    document = await db.scalar(
        select(Document).where(Document.id == document_id, Document.user_id == user.id)
    )
    if document is None:
        raise NotFoundError("文稿")
    await db.delete(document)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
