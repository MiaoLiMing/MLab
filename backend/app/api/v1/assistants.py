from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Response, status
from sqlalchemy import or_, select

from app.api.deps import CurrentUser, DBSession
from app.core.errors import AppError, NotFoundError
from app.models.entities import Assistant, AssistantInstallation, Visibility
from app.schemas.common import MessageResponse
from app.schemas.content import AssistantCreate, AssistantResponse, AssistantUpdate

router = APIRouter(prefix="/assistants", tags=["assistants"])


async def serialize_assistants(
    assistants: list[Assistant], user_id: UUID, db: DBSession
) -> list[AssistantResponse]:
    installed_ids = set(
        await db.scalars(
            select(AssistantInstallation.assistant_id).where(
                AssistantInstallation.user_id == user_id
            )
        )
    )
    responses: list[AssistantResponse] = []
    for item in assistants:
        data = AssistantResponse.model_validate(item).model_dump()
        data["installed"] = item.id in installed_ids
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


@router.post("", response_model=AssistantResponse, status_code=status.HTTP_201_CREATED)
async def create_assistant(
    payload: AssistantCreate, user: CurrentUser, db: DBSession
) -> AssistantResponse:
    assistant = Assistant(
        owner_id=user.id,
        slug=f"custom-{uuid4().hex[:12]}",
        visibility=Visibility.PRIVATE,
        **payload.model_dump(by_alias=True),
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
    await db.commit()
    await db.refresh(assistant)
    data = AssistantResponse.model_validate(assistant).model_dump()
    data["installed"] = True
    return AssistantResponse.model_validate(data)


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
    for field, value in payload.model_dump(exclude_unset=True, by_alias=True).items():
        setattr(assistant, field, value)
    await db.commit()
    await db.refresh(assistant)
    data = AssistantResponse.model_validate(assistant).model_dump()
    data["installed"] = True
    return AssistantResponse.model_validate(data)


@router.delete("/{assistant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assistant(assistant_id: UUID, user: CurrentUser, db: DBSession) -> Response:
    assistant = await db.scalar(
        select(Assistant).where(Assistant.id == assistant_id, Assistant.owner_id == user.id)
    )
    if assistant is None:
        raise NotFoundError("助手")
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
    await db.delete(installed)
    await db.commit()
    return MessageResponse(message="助手已移除")
