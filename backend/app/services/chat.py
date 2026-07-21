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
    AssistantFile,
    Conversation,
    FileAsset,
    Message,
    ModelConfig,
    ProviderCredential,
)
from app.services.memory import relevant_memories


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
    assistant_config: dict[str, object] = {}
    if conversation and conversation.assistant_id:
        assistant = await db.get(Assistant, conversation.assistant_id)
        if assistant:
            assistant_config = assistant.model_config or {}
    if settings.mock_ai_enabled:
        return ResolvedModel(
            provider="mock",
            model="mlab-mock",
            base_url="mock://local",
            api_key="mock",
            temperature=_temperature(assistant_config.get("temperature")),
            max_tokens=_max_tokens(assistant_config.get("max_tokens")),
        )
    config_id = requested_config_id or (conversation.model_config_id if conversation else None)
    if config_id is None and assistant_config.get("model_config_id"):
        try:
            config_id = UUID(str(assistant_config["model_config_id"]))
        except ValueError:
            config_id = None
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
            parameters = {**(config.parameters or {}), **assistant_config}
            return ResolvedModel(
                provider=config.provider,
                model=config.model_id,
                base_url=credential.base_url,
                api_key=decrypt_secret(credential.encrypted_api_key, settings),
                temperature=_temperature(parameters.get("temperature")),
                max_tokens=_max_tokens(parameters.get("max_tokens")),
            )

    if settings.ai_api_key:
        return ResolvedModel(
            provider=settings.default_ai_provider,
            model=config.model_id if config else settings.default_ai_model,
            base_url=settings.ai_base_url,
            api_key=settings.ai_api_key,
            temperature=_temperature(assistant_config.get("temperature")),
            max_tokens=_max_tokens(assistant_config.get("max_tokens")),
        )
    raise AppError("MODEL_NOT_CONFIGURED", "请先在设置中配置模型 API Key", 422)


def _temperature(value: object) -> float:
    try:
        return max(0.0, min(2.0, float(value if value is not None else 0.7)))
    except (TypeError, ValueError):
        return 0.7


def _max_tokens(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return max(1, min(100_000, int(value)))
    except (TypeError, ValueError):
        return None


async def build_prompt_messages(
    db: AsyncSession,
    conversation: Conversation,
    user_id: UUID,
    settings: Settings,
    memory_enabled: bool,
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    if conversation.assistant_id:
        assistant = await db.get(Assistant, conversation.assistant_id)
        if assistant and assistant.system_prompt:
            messages.append({"role": "system", "content": assistant.system_prompt})
        if assistant and assistant.owner_id == user_id:
            knowledge_files = await db.scalars(
                select(FileAsset)
                .join(AssistantFile, AssistantFile.file_id == FileAsset.id)
                .where(
                    AssistantFile.assistant_id == assistant.id,
                    FileAsset.user_id == user_id,
                    FileAsset.mime_type.in_(["text/plain", "text/markdown", "application/json"]),
                )
                .limit(10)
            )
            knowledge_parts: list[str] = []
            for asset in knowledge_files:
                path = settings.local_storage_path / asset.storage_key
                if path.exists() and path.stat().st_size <= 500_000:
                    knowledge_parts.append(
                        f"资料 {asset.original_name}：\n"
                        + path.read_text(encoding="utf-8", errors="replace")
                    )
            if knowledge_parts:
                messages.append(
                    {
                        "role": "system",
                        "content": "以下是该助手的私有知识资料，仅依据资料回答相关问题：\n\n"
                        + "\n\n".join(knowledge_parts),
                    }
                )
    memory_items: list[str] = []
    if memory_enabled:
        latest_user_message = next(
            (
                message.content
                for message in reversed(conversation.messages)
                if message.role == "user"
            ),
            "",
        )
        memories = await relevant_memories(db, user_id, latest_user_message)
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
