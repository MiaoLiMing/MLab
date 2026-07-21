from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Response, status
from sqlalchemy import or_, select

from app.api.deps import CurrentUser, DBSession
from app.core.errors import AppError, NotFoundError
from app.models.entities import (
    Assistant,
    AssistantFile,
    AssistantInstallation,
    FileAsset,
    ModelConfig,
    Visibility,
)
from app.schemas.common import MessageResponse
from app.schemas.content import AssistantCreate, AssistantResponse, AssistantUpdate

router = APIRouter(prefix="/assistants", tags=["assistants"])


async def ensure_model_config_owner(
    model_config_id: UUID | None, user_id: UUID, db: DBSession
) -> None:
    if model_config_id is None:
        return
    found = await db.scalar(
        select(ModelConfig.id).where(
            ModelConfig.id == model_config_id, ModelConfig.user_id == user_id
        )
    )
    if found is None:
        raise AppError("INVALID_MODEL_CONFIG", "助手模型配置不可用", 422)


async def serialize_assistants(
    assistants: list[Assistant], user_id: UUID, db: DBSession
) -> list[AssistantResponse]:
    assistant_ids = [item.id for item in assistants]
    installed_ids = set(
        await db.scalars(
            select(AssistantInstallation.assistant_id).where(
                AssistantInstallation.user_id == user_id
            )
        )
    )
    knowledge_file_ids: dict[UUID, list[UUID]] = {
        assistant_id: [] for assistant_id in assistant_ids
    }
    if assistant_ids:
        rows = await db.execute(
            select(AssistantFile.assistant_id, AssistantFile.file_id).where(
                AssistantFile.assistant_id.in_(assistant_ids)
            )
        )
        for assistant_id, file_id in rows:
            knowledge_file_ids[assistant_id].append(file_id)
    responses: list[AssistantResponse] = []
    for item in assistants:
        data = AssistantResponse.model_validate(item).model_dump()
        data["installed"] = item.id in installed_ids
        data["knowledge_file_ids"] = knowledge_file_ids[item.id]
        responses.append(AssistantResponse.model_validate(data))
    return responses


@router.get("", response_model=list[AssistantResponse])
async def list_assistants(
    user: CurrentUser, db: DBSession, q: str | None = None, category: str | None = None
) -> list[AssistantResponse]:
    query = select(Assistant).where(
        or_(
            Assistant.owner_id == user.id,
            Assistant.visibility.in_([Visibility.PUBLIC, Visibility.SYSTEM]),
        )
    )
    if q:
        term = f"%{q.strip()}%"
        query = query.where(or_(Assistant.name.ilike(term), Assistant.description.ilike(term)))
    if category:
        query = query.where(Assistant.category == category)
    result = await db.scalars(
        query.order_by(Assistant.is_featured.desc(), Assistant.usage_count.desc())
    )
    return await serialize_assistants(list(result), user.id, db)


@router.get("/installed", response_model=list[AssistantResponse])
async def list_installed(user: CurrentUser, db: DBSession) -> list[AssistantResponse]:
    result = await db.scalars(
        select(Assistant)
        .join(AssistantInstallation)
        .where(AssistantInstallation.user_id == user.id)
        .order_by(AssistantInstallation.installed_at.desc())
    )
    return await serialize_assistants(list(result), user.id, db)


@router.get("/{assistant_id}", response_model=AssistantResponse)
async def get_assistant(assistant_id: UUID, user: CurrentUser, db: DBSession) -> AssistantResponse:
    assistant = await db.scalar(
        select(Assistant).where(
            Assistant.id == assistant_id,
            or_(
                Assistant.owner_id == user.id,
                Assistant.visibility.in_([Visibility.PUBLIC, Visibility.SYSTEM]),
            ),
        )
    )
    if assistant is None:
        raise NotFoundError("助手")
    return (await serialize_assistants([assistant], user.id, db))[0]


@router.post("", response_model=AssistantResponse, status_code=status.HTTP_201_CREATED)
async def create_assistant(
    payload: AssistantCreate, user: CurrentUser, db: DBSession
) -> AssistantResponse:
    await ensure_model_config_owner(payload.assistant_config.model_config_id, user.id, db)
    data = payload.model_dump(by_alias=True)
    knowledge_file_ids = data.pop("knowledge_file_ids")
    if knowledge_file_ids:
        owned_file_ids = set(
            await db.scalars(
                select(FileAsset.id).where(
                    FileAsset.id.in_(knowledge_file_ids), FileAsset.user_id == user.id
                )
            )
        )
        if owned_file_ids != set(knowledge_file_ids):
            raise AppError("INVALID_KNOWLEDGE_FILE", "一个或多个知识文件不可用", 422)
    assistant = Assistant(
        owner_id=user.id,
        slug=f"custom-{uuid4().hex[:12]}",
        visibility=Visibility.PRIVATE,
        **data,
    )
    db.add(assistant)
    await db.flush()
    db.add(
        AssistantInstallation(
            user_id=user.id,
            assistant_id=assistant.id,
            installed_at=datetime.now(UTC),
        )
    )
    db.add_all(
        [
            AssistantFile(assistant_id=assistant.id, file_id=file_id)
            for file_id in knowledge_file_ids
        ]
    )
    await db.commit()
    await db.refresh(assistant)
    return (await serialize_assistants([assistant], user.id, db))[0]


@router.patch("/{assistant_id}", response_model=AssistantResponse)
async def update_assistant(
    assistant_id: UUID,
    payload: AssistantUpdate,
    user: CurrentUser,
    db: DBSession,
) -> AssistantResponse:
    assistant = await db.scalar(
        select(Assistant).where(Assistant.id == assistant_id, Assistant.owner_id == user.id)
    )
    if assistant is None:
        raise NotFoundError("助手")
    if payload.assistant_config is not None:
        await ensure_model_config_owner(payload.assistant_config.model_config_id, user.id, db)
    changes = payload.model_dump(exclude_unset=True, by_alias=True)
    knowledge_file_ids = changes.pop("knowledge_file_ids", None)
    if knowledge_file_ids is not None:
        owned_file_ids = set(
            await db.scalars(
                select(FileAsset.id).where(
                    FileAsset.id.in_(knowledge_file_ids), FileAsset.user_id == user.id
                )
            )
        )
        if owned_file_ids != set(knowledge_file_ids):
            raise AppError("INVALID_KNOWLEDGE_FILE", "一个或多个知识文件不可用", 422)
        existing_files = list(
            await db.scalars(
                select(AssistantFile).where(AssistantFile.assistant_id == assistant.id)
            )
        )
        for existing in existing_files:
            await db.delete(existing)
        db.add_all(
            [
                AssistantFile(assistant_id=assistant.id, file_id=file_id)
                for file_id in knowledge_file_ids
            ]
        )
    for field, value in changes.items():
        setattr(assistant, field, value)
    await db.commit()
    await db.refresh(assistant)
    return (await serialize_assistants([assistant], user.id, db))[0]


@router.delete("/{assistant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assistant(assistant_id: UUID, user: CurrentUser, db: DBSession) -> Response:
    assistant = await db.scalar(
        select(Assistant).where(Assistant.id == assistant_id, Assistant.owner_id == user.id)
    )
    if assistant is None:
        raise NotFoundError("助手")
    if user.default_assistant_id == assistant.id:
        user.default_assistant_id = None
    await db.delete(assistant)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{assistant_id}/install", response_model=MessageResponse)
async def install_assistant(
    assistant_id: UUID, user: CurrentUser, db: DBSession
) -> MessageResponse:
    assistant = await db.scalar(
        select(Assistant).where(
            Assistant.id == assistant_id,
            or_(
                Assistant.owner_id == user.id,
                Assistant.visibility.in_([Visibility.PUBLIC, Visibility.SYSTEM]),
            ),
        )
    )
    if assistant is None:
        raise NotFoundError("助手")
    installed = await db.scalar(
        select(AssistantInstallation).where(
            AssistantInstallation.user_id == user.id,
            AssistantInstallation.assistant_id == assistant_id,
        )
    )
    if installed:
        raise AppError("ALREADY_INSTALLED", "该助手已安装", 409)
    db.add(AssistantInstallation(user_id=user.id, assistant_id=assistant_id))
    assistant.usage_count += 1
    await db.commit()
    return MessageResponse(message="助手已安装")


@router.delete("/{assistant_id}/install", response_model=MessageResponse)
async def uninstall_assistant(
    assistant_id: UUID, user: CurrentUser, db: DBSession
) -> MessageResponse:
    installed = await db.scalar(
        select(AssistantInstallation).where(
            AssistantInstallation.user_id == user.id,
            AssistantInstallation.assistant_id == assistant_id,
        )
    )
    if installed is None:
        raise NotFoundError("助手安装记录")
    if user.default_assistant_id == assistant_id:
        user.default_assistant_id = None
    await db.delete(installed)
    await db.commit()
    return MessageResponse(message="助手已移除")
