from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.ai.provider import OpenAICompatibleProvider, ProviderError, ProviderRequest
from app.ai.runtime import generation_registry
from app.api.deps import AppSettings, CurrentUser, DBSession
from app.core.errors import AppError
from app.models.entities import (
    Conversation,
    FileAsset,
    Message,
    MessageAttachment,
    MessageRole,
    MessageStatus,
    UsageRecord,
)
from app.schemas.common import MessageResponse as OperationResponse
from app.schemas.content import (
    ConversationCreate,
    ConversationDetail,
    ConversationResponse,
    ConversationUpdate,
    SendMessageRequest,
)
from app.services.chat import build_prompt_messages, get_owned_conversation, resolve_model
from app.tasks.queue import enqueue_memory_extraction

router = APIRouter(prefix="/conversations", tags=["conversations"])


def sse(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(user: CurrentUser, db: DBSession) -> list[Conversation]:
    result = await db.scalars(
        select(Conversation)
        .where(Conversation.user_id == user.id, Conversation.archived_at.is_(None))
        .order_by(Conversation.updated_at.desc())
        .limit(100)
    )
    return list(result)


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreate, user: CurrentUser, db: DBSession
) -> Conversation:
    conversation = Conversation(user_id=user.id, **payload.model_dump())
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: UUID, user: CurrentUser, db: DBSession) -> Conversation:
    return await get_owned_conversation(db, conversation_id, user.id, with_messages=True)


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: UUID,
    payload: ConversationUpdate,
    user: CurrentUser,
    db: DBSession,
) -> Conversation:
    conversation = await get_owned_conversation(db, conversation_id, user.id)
    changes = payload.model_dump(exclude_unset=True)
    if "archived" in changes:
        conversation.archived_at = datetime.now(UTC) if changes.pop("archived") else None
    for field, value in changes.items():
        setattr(conversation, field, value)
    await db.commit()
    await db.refresh(conversation)
    return conversation


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(conversation_id: UUID, user: CurrentUser, db: DBSession) -> Response:
    conversation = await get_owned_conversation(db, conversation_id, user.id)
    await db.delete(conversation)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{conversation_id}/messages")
async def send_message(
    conversation_id: UUID,
    payload: SendMessageRequest,
    user: CurrentUser,
    db: DBSession,
    settings: AppSettings,
) -> StreamingResponse:
    conversation = await get_owned_conversation(db, conversation_id, user.id, with_messages=True)
    model = await resolve_model(db, settings, user.id, payload.model_config_id, conversation)
    now = datetime.now(UTC)
    user_message = Message(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        content=payload.content.strip(),
        status=MessageStatus.COMPLETED,
        model=None,
        created_at=now,
        updated_at=now,
    )
    db.add(user_message)
    await db.flush()
    attachment_context: list[str] = []
    if payload.attachment_ids:
        files = list(
            await db.scalars(
                select(FileAsset).where(
                    FileAsset.id.in_(payload.attachment_ids), FileAsset.user_id == user.id
                )
            )
        )
        if len(files) != len(set(payload.attachment_ids)):
            raise AppError("INVALID_ATTACHMENT", "一个或多个附件不可用", 422)
        for asset in files:
            db.add(
                MessageAttachment(
                    message_id=user_message.id,
                    file_id=asset.id,
                    attachment_type="file",
                    attachment_metadata={"name": asset.original_name, "mime_type": asset.mime_type},
                )
            )
            if asset.mime_type in {"text/plain", "text/markdown", "application/json"}:
                path = settings.local_storage_path / asset.storage_key
                if path.exists() and path.stat().st_size <= 200_000:
                    attachment_text = path.read_text(encoding="utf-8", errors="replace")
                    attachment_context.append(f"附件 {asset.original_name}：\n{attachment_text}")
    assistant_message = Message(
        conversation_id=conversation.id,
        parent_id=user_message.id,
        role=MessageRole.ASSISTANT,
        content="",
        status=MessageStatus.STREAMING,
        model=model.model,
        created_at=now,
        updated_at=now,
    )
    db.add(assistant_message)
    if conversation.title == "新对话":
        conversation.title = payload.content.strip().replace("\n", " ")[:40]
    await db.commit()
    await db.refresh(assistant_message)
    await db.refresh(conversation, attribute_names=["messages"])
    prompt = await build_prompt_messages(db, conversation, user.id)
    if attachment_context and prompt:
        prompt[-1]["content"] += "\n\n" + "\n\n".join(attachment_context)

    async def generate() -> AsyncIterator[str]:
        cancel_event = await generation_registry.register(assistant_message.id)
        content_parts: list[str] = []
        input_tokens = 0
        output_tokens = 0
        yield sse("message.start", {"message_id": str(assistant_message.id)})
        provider = OpenAICompatibleProvider(model.base_url, model.api_key)
        try:
            request = ProviderRequest(
                model=model.model,
                messages=prompt,
                temperature=model.temperature,
                max_tokens=model.max_tokens,
            )
            async for event in provider.stream_chat(request):
                if cancel_event.is_set():
                    assistant_message.status = MessageStatus.STOPPED
                    break
                if event.kind == "delta":
                    content_parts.append(event.content)
                    yield sse("message.delta", {"content": event.content})
                elif event.kind == "usage":
                    input_tokens = event.input_tokens
                    output_tokens = event.output_tokens
            else:
                assistant_message.status = MessageStatus.COMPLETED
            assistant_message.content = "".join(content_parts)
            assistant_message.input_tokens = input_tokens
            assistant_message.output_tokens = output_tokens
            assistant_message.updated_at = datetime.now(UTC)
            db.add(
                UsageRecord(
                    user_id=user.id,
                    conversation_id=conversation.id,
                    provider=model.provider,
                    model=model.model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_microunits=None,
                )
            )
            await db.commit()
            await enqueue_memory_extraction(str(user.id), payload.content)
            yield sse(
                "message.done",
                {
                    "status": assistant_message.status,
                    "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
                },
            )
        except ProviderError as exc:
            assistant_message.content = "".join(content_parts)
            assistant_message.status = MessageStatus.FAILED
            assistant_message.error_code = exc.code
            assistant_message.updated_at = datetime.now(UTC)
            await db.commit()
            yield sse("error", {"code": exc.code, "message": exc.message})
        finally:
            await generation_registry.remove(assistant_message.id)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/messages/{message_id}/stop", response_model=OperationResponse)
async def stop_message(message_id: UUID, user: CurrentUser, db: DBSession) -> OperationResponse:
    message = await db.scalar(
        select(Message)
        .join(Conversation)
        .where(Message.id == message_id, Conversation.user_id == user.id)
    )
    if message is None:
        raise AppError("NOT_FOUND", "消息不存在", 404)
    stopped = await generation_registry.stop(message_id)
    return OperationResponse(message="已发送停止请求" if stopped else "消息未在生成中")
