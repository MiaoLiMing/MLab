from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DBSession
from app.core.errors import AppError
from app.models.entities import (
    Assistant,
    AssistantInstallation,
    Conversation,
    Document,
    Task,
    UsageRecord,
)
from app.schemas.auth import UsageSummary, UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_profile(user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(user)


@router.patch("/me", response_model=UserResponse)
async def update_profile(payload: UserUpdate, user: CurrentUser, db: DBSession) -> UserResponse:
    changes = payload.model_dump(exclude_unset=True)
    default_assistant_id = changes.get("default_assistant_id")
    if default_assistant_id:
        allowed = await db.scalar(
            select(Assistant.id)
            .outerjoin(
                AssistantInstallation,
                (AssistantInstallation.assistant_id == Assistant.id)
                & (AssistantInstallation.user_id == user.id),
            )
            .where(
                Assistant.id == default_assistant_id,
                (Assistant.owner_id == user.id) | (AssistantInstallation.id.is_not(None)),
            )
        )
        if allowed is None:
            raise AppError("INVALID_ASSISTANT", "默认助手不可用或尚未安装", 422)
    for field, value in changes.items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.get("/me/usage", response_model=UsageSummary)
async def get_usage_summary(user: CurrentUser, db: DBSession) -> UsageSummary:
    conversations = await db.scalar(
        select(func.count(Conversation.id)).where(Conversation.user_id == user.id)
    )
    tasks = await db.scalar(select(func.count(Task.id)).where(Task.user_id == user.id))
    documents = await db.scalar(select(func.count(Document.id)).where(Document.user_id == user.id))
    tokens = await db.execute(
        select(
            func.coalesce(func.sum(UsageRecord.input_tokens), 0),
            func.coalesce(func.sum(UsageRecord.output_tokens), 0),
        ).where(UsageRecord.user_id == user.id)
    )
    input_tokens, output_tokens = tokens.one()
    return UsageSummary(
        conversations=int(conversations or 0),
        tasks=int(tasks or 0),
        documents=int(documents or 0),
        input_tokens=int(input_tokens),
        output_tokens=int(output_tokens),
    )
