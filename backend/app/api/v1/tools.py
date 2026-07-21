from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import or_, select

from app.api.deps import CurrentUser, DBSession
from app.core.errors import AppError, NotFoundError
from app.models.entities import Conversation, Message, ToolDefinition, ToolFavorite
from app.schemas.common import MessageResponse
from app.schemas.content import ToolExecuteRequest, ToolExecuteResponse, ToolResponse
from app.services.tools import record_tool_execution, run_builtin_tool

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("", response_model=list[ToolResponse])
async def list_tools(
    user: CurrentUser, db: DBSession, q: str | None = None, category: str | None = None
) -> list[ToolResponse]:
    query = select(ToolDefinition).where(ToolDefinition.is_active.is_(True))
    if q:
        term = f"%{q.strip()}%"
        query = query.where(
            or_(ToolDefinition.name.ilike(term), ToolDefinition.description.ilike(term))
        )
    if category:
        query = query.where(ToolDefinition.category == category)
    tools = list(await db.scalars(query.order_by(ToolDefinition.rating.desc())))
    favorites = set(
        await db.scalars(select(ToolFavorite.tool_id).where(ToolFavorite.user_id == user.id))
    )
    responses: list[ToolResponse] = []
    for tool in tools:
        data = ToolResponse.model_validate(tool).model_dump()
        data["is_favorite"] = tool.id in favorites
        responses.append(ToolResponse.model_validate(data))
    return responses


@router.post("/{tool_id}/favorite", response_model=MessageResponse)
async def favorite_tool(tool_id: UUID, user: CurrentUser, db: DBSession) -> MessageResponse:
    if await db.get(ToolDefinition, tool_id) is None:
        raise NotFoundError("工具")
    favorite = await db.scalar(
        select(ToolFavorite).where(ToolFavorite.user_id == user.id, ToolFavorite.tool_id == tool_id)
    )
    if favorite is None:
        db.add(ToolFavorite(user_id=user.id, tool_id=tool_id))
        message = "已收藏"
    else:
        await db.delete(favorite)
        message = "已取消收藏"
    await db.commit()
    return MessageResponse(message=message)


@router.post("/{tool_id}/execute", response_model=ToolExecuteResponse)
async def execute_tool(
    tool_id: UUID, payload: ToolExecuteRequest, user: CurrentUser, db: DBSession
) -> ToolExecuteResponse:
    tool = await db.scalar(
        select(ToolDefinition).where(
            ToolDefinition.id == tool_id, ToolDefinition.is_active.is_(True)
        )
    )
    if tool is None:
        raise NotFoundError("工具")
    if tool.access_type != "openai_tool":
        raise AppError("TOOL_NOT_EXECUTABLE", "该工具仅提供外部访问", 422)
    if payload.message_id:
        owned_message = await db.scalar(
            select(Message.id)
            .join(Conversation)
            .where(Message.id == payload.message_id, Conversation.user_id == user.id)
        )
        if owned_message is None:
            raise AppError("INVALID_MESSAGE", "消息不可用", 422)

    output = run_builtin_tool(tool, payload.input)
    execution = await record_tool_execution(
        db,
        user.id,
        tool,
        payload.input,
        output,
        payload.message_id,
    )
    await db.commit()
    await db.refresh(execution)
    return ToolExecuteResponse(execution_id=execution.id, output=output)
