import ipaddress
from time import perf_counter
from urllib.parse import urlparse
from uuid import UUID

import httpx
from fastapi import APIRouter, Response, status
from sqlalchemy import select, update

from app.api.deps import AppSettings, CurrentUser, DBSession
from app.core.errors import AppError, NotFoundError
from app.core.security import encrypt_secret, mask_secret
from app.models.entities import ModelConfig, ProviderCredential
from app.schemas.common import MessageResponse
from app.schemas.models import (
    CredentialCreate,
    CredentialResponse,
    CredentialTestRequest,
    CredentialTestResponse,
    ModelConfigCreate,
    ModelConfigResponse,
    ModelConfigUpdate,
    ProviderInfo,
)

router = APIRouter(tags=["model-settings"])

PROVIDERS = [
    ProviderInfo(
        id="openai",
        name="OpenAI",
        base_url="https://api.openai.com/v1",
        example_models=["gpt-4.1-mini", "gpt-4.1"],
    ),
    ProviderInfo(
        id="deepseek",
        name="DeepSeek",
        base_url="https://api.deepseek.com/v1",
        example_models=["deepseek-chat", "deepseek-reasoner"],
    ),
    ProviderInfo(
        id="qwen",
        name="通义千问",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        example_models=["qwen-plus", "qwen-max"],
    ),
    ProviderInfo(
        id="moonshot",
        name="Moonshot",
        base_url="https://api.moonshot.cn/v1",
        example_models=["moonshot-v1-8k"],
    ),
    ProviderInfo(
        id="zhipu",
        name="智谱 AI",
        base_url="https://open.bigmodel.cn/api/paas/v4",
        example_models=["glm-4-flash", "glm-4-plus"],
    ),
]


@router.get("/providers", response_model=list[ProviderInfo])
async def list_providers(_user: CurrentUser) -> list[ProviderInfo]:
    return PROVIDERS


def validate_provider_url(value: str) -> str:
    url = value.rstrip("/")
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not hostname:
        raise AppError("INVALID_PROVIDER_URL", "模型地址必须是有效的 HTTPS URL", 422)
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise AppError("INVALID_PROVIDER_URL", "模型地址不能指向本机", 422)
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return url
    if not address.is_global:
        raise AppError("INVALID_PROVIDER_URL", "模型地址不能指向私网或保留地址", 422)
    return url


@router.get("/provider-credentials", response_model=list[CredentialResponse])
async def list_credentials(user: CurrentUser, db: DBSession) -> list[ProviderCredential]:
    result = await db.scalars(
        select(ProviderCredential)
        .where(ProviderCredential.user_id == user.id)
        .order_by(ProviderCredential.created_at.desc())
    )
    return list(result)


@router.post(
    "/provider-credentials",
    response_model=CredentialResponse,
    status_code=status.HTTP_201_CREATED,
)
async def save_credential(
    payload: CredentialCreate, user: CurrentUser, db: DBSession, settings: AppSettings
) -> ProviderCredential:
    credential = await db.scalar(
        select(ProviderCredential).where(
            ProviderCredential.user_id == user.id,
            ProviderCredential.provider == payload.provider,
        )
    )
    if credential is None:
        credential = ProviderCredential(user_id=user.id, provider=payload.provider)
        db.add(credential)
    credential.display_name = payload.display_name
    credential.base_url = validate_provider_url(str(payload.base_url))
    credential.encrypted_api_key = encrypt_secret(payload.api_key, settings)
    credential.key_hint = mask_secret(payload.api_key)
    credential.is_active = True
    await db.commit()
    await db.refresh(credential)
    return credential


@router.delete("/provider-credentials/{credential_id}", response_model=MessageResponse)
async def delete_credential(
    credential_id: UUID, user: CurrentUser, db: DBSession
) -> MessageResponse:
    credential = await db.scalar(
        select(ProviderCredential).where(
            ProviderCredential.id == credential_id, ProviderCredential.user_id == user.id
        )
    )
    if credential is None:
        raise NotFoundError("模型凭据")
    await db.delete(credential)
    await db.commit()
    return MessageResponse(message="模型凭据已删除")


@router.post("/provider-credentials/test", response_model=CredentialTestResponse)
async def test_credential(
    payload: CredentialTestRequest, _user: CurrentUser
) -> CredentialTestResponse:
    started = perf_counter()
    url = f"{validate_provider_url(str(payload.base_url))}/models"
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.get(url, headers={"Authorization": f"Bearer {payload.api_key}"})
            response.raise_for_status()
            body = response.json()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in {401, 403}:
            raise AppError("MODEL_AUTH_FAILED", "API Key 验证失败", 422) from None
        raise AppError("MODEL_CONNECTION_FAILED", "模型服务返回异常", 422) from None
    except (httpx.HTTPError, ValueError):
        raise AppError("MODEL_CONNECTION_FAILED", "无法连接模型服务", 422) from None
    models = [str(item.get("id")) for item in body.get("data", []) if item.get("id")]
    return CredentialTestResponse(
        ok=True,
        latency_ms=int((perf_counter() - started) * 1000),
        models=models[:100],
        message="连接成功",
    )


@router.get("/model-configs", response_model=list[ModelConfigResponse])
async def list_model_configs(user: CurrentUser, db: DBSession) -> list[ModelConfig]:
    result = await db.scalars(
        select(ModelConfig)
        .where(ModelConfig.user_id == user.id)
        .order_by(ModelConfig.is_default.desc(), ModelConfig.created_at.desc())
    )
    return list(result)


async def ensure_credential_owner(credential_id: UUID | None, user_id: UUID, db: DBSession) -> None:
    if credential_id is None:
        return
    found = await db.scalar(
        select(ProviderCredential.id).where(
            ProviderCredential.id == credential_id, ProviderCredential.user_id == user_id
        )
    )
    if found is None:
        raise AppError("INVALID_CREDENTIAL", "模型凭据不可用", 422)


@router.post("/model-configs", response_model=ModelConfigResponse, status_code=201)
async def create_model_config(
    payload: ModelConfigCreate, user: CurrentUser, db: DBSession
) -> ModelConfig:
    await ensure_credential_owner(payload.credential_id, user.id, db)
    if payload.is_default:
        await db.execute(
            update(ModelConfig).where(ModelConfig.user_id == user.id).values(is_default=False)
        )
    model = ModelConfig(user_id=user.id, **payload.model_dump())
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return model


@router.patch("/model-configs/{config_id}", response_model=ModelConfigResponse)
async def update_model_config(
    config_id: UUID, payload: ModelConfigUpdate, user: CurrentUser, db: DBSession
) -> ModelConfig:
    model = await db.scalar(
        select(ModelConfig).where(ModelConfig.id == config_id, ModelConfig.user_id == user.id)
    )
    if model is None:
        raise NotFoundError("模型配置")
    if payload.is_default:
        await db.execute(
            update(ModelConfig).where(ModelConfig.user_id == user.id).values(is_default=False)
        )
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(model, field, value)
    await db.commit()
    await db.refresh(model)
    return model


@router.delete("/model-configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_model_config(config_id: UUID, user: CurrentUser, db: DBSession) -> Response:
    model = await db.scalar(
        select(ModelConfig).where(ModelConfig.id == config_id, ModelConfig.user_id == user.id)
    )
    if model is None:
        raise NotFoundError("模型配置")
    await db.delete(model)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
