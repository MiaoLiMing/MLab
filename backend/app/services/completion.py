from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.provider import ProviderError, ProviderRequest, create_provider
from app.core.config import Settings
from app.core.errors import AppError
from app.services.chat import resolve_model


async def complete_text(
    db: AsyncSession,
    settings: Settings,
    user_id: UUID,
    prompt: str,
    *,
    system_prompt: str,
    model_config_id: UUID | None = None,
) -> str:
    """Run a short non-streaming application action through the shared provider gateway."""

    model = await resolve_model(db, settings, user_id, model_config_id)
    provider = create_provider(model.provider, model.base_url, model.api_key, timeout=90)
    parts: list[str] = []
    try:
        async for event in provider.stream_chat(
            ProviderRequest(
                model=model.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=model.temperature,
                max_tokens=model.max_tokens,
            )
        ):
            if event.kind == "delta":
                parts.append(event.content)
    except ProviderError as exc:
        raise AppError(exc.code, exc.message, 502) from exc
    result = "".join(parts).strip()
    if not result:
        raise AppError("EMPTY_MODEL_RESPONSE", "模型没有返回内容", 502)
    return result
