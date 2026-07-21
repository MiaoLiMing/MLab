from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings
from app.core.errors import AppError, NotFoundError
from app.core.security import decrypt_secret
from app.models.entities import (
    Assistant,
    Conversation,
    Memory,
    Message,
    ModelConfig,
    ProviderCredential,
)


@dataclass(slots=True)
class ResolvedModel:
    provider: str
    model: str
    base_url: str
    api_key: str
    temperature: float
    max_tokens: int | None


async def get_owned_conversation(
    db: AsyncSession, conversation_id: UUID, user_id: UUID, with_messages: bool = False
) -> Conversation:
    query = select(Conversation).where(
        Conversation.id == conversation_id, Conversation.user_id == user_id
    )
    if with_messages:
        query = query.options(selectinload(Conversation.messages).selectinload(Message.attachments))
    conversation = await db.scalar(query)
    if conversation is None:
        raise NotFoundError("会话")
    return conversation


async def resolve_model(
    db: AsyncSession,
    settings: Settings,
    user_id: UUID,
    requested_config_id: UUID | None,
    conversation: Conversation | None = None,
) -> ResolvedModel:
    config_id = requested_config_id or (conversation.model_config_id if conversation else None)
    config: ModelConfig | None = None
    if config_id:
        config = await db.scalar(
            select(ModelConfig).where(ModelConfig.id == config_id, ModelConfig.user_id == user_id)
        )
        if config is None:
            raise AppError("INVALID_MODEL_CONFIG", "模型配置不可用", 422)
    else:
        config = await db.scalar(
            select(ModelConfig).where(
                ModelConfig.user_id == user_id, ModelConfig.is_default.is_(True)
            )
        )

    if config:
        credential = None
        if config.credential_id:
            credential = await db.scalar(
                select(ProviderCredential).where(
                    ProviderCredential.id == config.credential_id,
                    ProviderCredential.user_id == user_id,
                    ProviderCredential.is_active.is_(True),
                )
            )
        if credential is None:
            credential = await db.scalar(
                select(ProviderCredential).where(
                    ProviderCredential.user_id == user_id,
                    ProviderCredential.provider == config.provider,
                    ProviderCredential.is_active.is_(True),
                )
            )
        if credential:
            parameters = config.parameters or {}
            return ResolvedModel(
                provider=config.provider,
                model=config.model_id,
                base_url=credential.base_url,
                api_key=decrypt_secret(credential.encrypted_api_key, settings),
                temperature=float(parameters.get("temperature", 0.7)),
                max_tokens=parameters.get("max_tokens"),
            )

    if settings.ai_api_key:
        return ResolvedModel(
            provider=settings.default_ai_provider,
            model=config.model_id if config else settings.default_ai_model,
            base_url=settings.ai_base_url,
            api_key=settings.ai_api_key,
            temperature=0.7,
            max_tokens=None,
        )
    raise AppError("MODEL_NOT_CONFIGURED", "请先在设置中配置模型 API Key", 422)


async def build_prompt_messages(
    db: AsyncSession, conversation: Conversation, user_id: UUID
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    if conversation.assistant_id:
        assistant = await db.get(Assistant, conversation.assistant_id)
        if assistant and assistant.system_prompt:
            messages.append({"role": "system", "content": assistant.system_prompt})
    memories = await db.scalars(
        select(Memory)
        .where(Memory.user_id == user_id, Memory.enabled.is_(True))
        .order_by(Memory.updated_at.desc())
        .limit(6)
    )
    memory_items = [item.content for item in memories]
    if memory_items:
        messages.append(
            {
                "role": "system",
                "content": "以下是用户主动保存的记忆，仅在相关时自然使用：\n- "
                + "\n- ".join(memory_items),
            }
        )
    messages.extend(
        {"role": message.role, "content": message.content}
        for message in conversation.messages
        if message.role in {"user", "assistant"} and message.content
    )
    return messages
