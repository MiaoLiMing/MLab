from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from time import monotonic
from uuid import UUID

from fastapi import APIRouter, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, or_, select

from app.ai.provider import ProviderError, ProviderRequest, create_provider
from app.ai.runtime import generation_registry
from app.api.deps import AppSettings, CurrentUser, DBSession
from app.core.errors import AppError
from app.models.entities import (
    Assistant,
    AssistantInstallation,
    Conversation,
    FileAsset,
    Message,
    MessageAttachment,
    MessageRole,
    MessageStatus,
    ToolDefinition,
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
from app.services.tools import record_tool_execution, run_builtin_tool
from app.tasks.queue import enqueue_memory_extraction

router = APIRouter(prefix="/conversations", tags=["conversations"])

BUILTIN_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "计算基础算术表达式。需要精确计算时使用。",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "current-time",
            "description": "查询指定 IANA 时区的当前日期和时间。",
            "parameters": {
                "type": "object",
                "properties": {"timezone": {"type": "string", "description": "例如 Asia/Shanghai"}},
                "required": ["timezone"],
                "additionalProperties": False,
            },
        },
    },
]


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
    assistant_id = payload.assistant_id or user.default_assistant_id
    if assistant_id:
        assistant = await db.scalar(
            select(Assistant)
            .outerjoin(
                AssistantInstallation,
                (AssistantInstallation.assistant_id == Assistant.id)
                & (AssistantInstallation.user_id == user.id),
            )
            .where(
                Assistant.id == assistant_id,
                or_(Assistant.owner_id == user.id, AssistantInstallation.id.is_not(None)),
            )
        )
        if assistant is None:
            raise AppError("INVALID_ASSISTANT", "助手不可用或尚未安装", 422)
    conversation = Conversation(
        user_id=user.id,
        title=payload.title,
        assistant_id=assistant_id,
        model_config_id=payload.model_config_id,
    )
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
    user_message: Message | None = None
    if payload.source_message_id:
        source_index = next(
            (
                index
                for index, message in enumerate(conversation.messages)
                if message.id == payload.source_message_id and message.role == MessageRole.USER
            ),
            -1,
        )
        user_message = conversation.messages[source_index] if source_index >= 0 else None
        if user_message is None:
            raise AppError("INVALID_SOURCE_MESSAGE", "只能从当前会话的用户消息重新生成", 422)
        stale_message_ids = [message.id for message in conversation.messages[source_index + 1 :]]
        if stale_message_ids:
            await db.execute(delete(Message).where(Message.id.in_(stale_message_ids)))
        user_message.content = payload.content.strip()
        user_message.updated_at = now
    else:
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
    assert user_message is not None
    attachment_context: list[str] = []
    effective_attachment_ids = payload.attachment_ids
    if payload.source_message_id and not effective_attachment_ids:
        effective_attachment_ids = [attachment.file_id for attachment in user_message.attachments]
    if payload.source_message_id and payload.attachment_ids:
        for attachment in list(user_message.attachments):
            await db.delete(attachment)
    if effective_attachment_ids:
        files = list(
            await db.scalars(
                select(FileAsset).where(
                    FileAsset.id.in_(effective_attachment_ids), FileAsset.user_id == user.id
                )
            )
        )
        if len(files) != len(set(effective_attachment_ids)):
            raise AppError("INVALID_ATTACHMENT", "一个或多个附件不可用", 422)
        for asset in files:
            if payload.source_message_id is None or payload.attachment_ids:
                db.add(
                    MessageAttachment(
                        message_id=user_message.id,
                        file_id=asset.id,
                        attachment_type="file",
                        attachment_metadata={
                            "name": asset.original_name,
                            "mime_type": asset.mime_type,
                        },
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
    db.expire(conversation, ["messages"])
    await db.refresh(conversation, attribute_names=["messages"])
    prompt = await build_prompt_messages(db, conversation, user.id, settings, user.memory_enabled)
    if attachment_context and prompt:
        prompt[-1]["content"] += "\n\n" + "\n\n".join(attachment_context)
    executable_tools = list(
        await db.scalars(
            select(ToolDefinition).where(
                ToolDefinition.slug.in_(["calculator", "current-time"]),
                ToolDefinition.access_type == "openai_tool",
                ToolDefinition.is_active.is_(True),
            )
        )
    )
    tools_by_slug = {tool.slug: tool for tool in executable_tools}

    async def generate() -> AsyncIterator[str]:
        cancel_event = await generation_registry.register(assistant_message.id)
        content_parts: list[str] = []
        input_tokens = 0
        output_tokens = 0
        last_persisted_at = monotonic()
        tool_calls: dict[int, dict[str, str]] = {}
        yield sse("message.start", {"message_id": str(assistant_message.id)})
        provider = create_provider(model.provider, model.base_url, model.api_key)
        try:
            request = ProviderRequest(
                model=model.model,
                messages=prompt,
                temperature=model.temperature,
                max_tokens=model.max_tokens,
                tools=[
                    schema
                    for schema in BUILTIN_TOOL_SCHEMAS
                    if schema["function"]["name"] in tools_by_slug
                ],
            )
            async for event in provider.stream_chat(request):
                if cancel_event.is_set():
                    assistant_message.status = MessageStatus.STOPPED
                    break
                if event.kind == "delta":
                    content_parts.append(event.content)
                    yield sse("message.delta", {"content": event.content})
                    if monotonic() - last_persisted_at >= 2:
                        assistant_message.content = "".join(content_parts)
                        assistant_message.updated_at = datetime.now(UTC)
                        await db.commit()
                        last_persisted_at = monotonic()
                elif event.kind == "usage":
                    input_tokens = event.input_tokens
                    output_tokens = event.output_tokens
                elif event.kind == "tool_delta":
                    call = tool_calls.setdefault(
                        event.tool_index, {"id": "", "name": "", "arguments": ""}
                    )
                    if event.tool_call_id:
                        call["id"] = event.tool_call_id
                    if event.tool_name:
                        call["name"] = event.tool_name
                    call["arguments"] += event.tool_arguments

            if tool_calls and not cancel_event.is_set():
                followup_messages = [*prompt]
                normalized_calls: list[dict[str, object]] = []
                tool_results: list[dict[str, object]] = []
                for index, call in sorted(tool_calls.items()):
                    if index >= 4:
                        break
                    call_id = call["id"] or f"tool-{assistant_message.id}-{index}"
                    name = call["name"]
                    try:
                        arguments = json.loads(call["arguments"] or "{}")
                        if not isinstance(arguments, dict):
                            raise ValueError
                    except (json.JSONDecodeError, ValueError):
                        arguments = {}
                    yield sse(
                        "tool.call",
                        {"tool_call_id": call_id, "name": name, "arguments": arguments},
                    )
                    tool = tools_by_slug.get(name)
                    if tool is None:
                        result: dict[str, object] = {"error": "工具不可用"}
                    else:
                        try:
                            result = run_builtin_tool(tool, arguments)
                            await record_tool_execution(
                                db,
                                user.id,
                                tool,
                                arguments,
                                result,
                                assistant_message.id,
                            )
                        except AppError as exc:
                            result = {"error": exc.message, "code": exc.code}
                    yield sse("tool.result", {"tool_call_id": call_id, "result": result})
                    normalized_calls.append(
                        {
                            "id": call_id,
                            "type": "function",
                            "function": {
                                "name": name,
                                "arguments": json.dumps(arguments, ensure_ascii=False),
                            },
                        }
                    )
                    tool_results.append(
                        {
                            "role": "tool",
                            "tool_call_id": call_id,
                            "content": json.dumps(result, ensure_ascii=False),
                        }
                    )
                followup_messages.append(
                    {
                        "role": "assistant",
                        "content": "".join(content_parts) or None,
                        "tool_calls": normalized_calls,
                    }
                )
                followup_messages.extend(tool_results)
                followup = ProviderRequest(
                    model=model.model,
                    messages=followup_messages,
                    temperature=model.temperature,
                    max_tokens=model.max_tokens,
                )
                async for event in provider.stream_chat(followup):
                    if cancel_event.is_set():
                        break
                    if event.kind == "delta":
                        content_parts.append(event.content)
                        yield sse("message.delta", {"content": event.content})
                    elif event.kind == "usage":
                        input_tokens += event.input_tokens
                        output_tokens += event.output_tokens

            assistant_message.status = (
                MessageStatus.STOPPED if cancel_event.is_set() else MessageStatus.COMPLETED
            )
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
        except asyncio.CancelledError:
            assistant_message.content = "".join(content_parts)
            assistant_message.status = MessageStatus.STOPPED
            assistant_message.updated_at = datetime.now(UTC)
            await db.commit()
            raise
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
    if stopped:
        message.status = MessageStatus.STOPPED
        message.updated_at = datetime.now(UTC)
        await db.commit()
    return OperationResponse(message="已发送停止请求" if stopped else "消息未在生成中")
