import ast
import math
import operator
from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter
from sqlalchemy import or_, select

from app.api.deps import CurrentUser, DBSession
from app.core.errors import AppError, NotFoundError
from app.models.entities import Conversation, Message, ToolDefinition, ToolExecution, ToolFavorite
from app.schemas.common import MessageResponse
from app.schemas.content import ToolExecuteRequest, ToolExecuteResponse, ToolResponse

router = APIRouter(prefix="/tools", tags=["tools"])

OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}


def evaluate_expression(expression: str) -> int | float:
    if not expression or len(expression) > 200:
        raise AppError("INVALID_EXPRESSION", "请输入长度不超过 200 的算式", 422)

    def evaluate(node: ast.AST) -> int | float:
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = evaluate(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.BinOp) and type(node.op) in OPERATORS:
            left, right = evaluate(node.left), evaluate(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 10:
                raise AppError("EXPRESSION_TOO_COMPLEX", "指数绝对值不能超过 10", 422)
            return OPERATORS[type(node.op)](left, right)
        raise AppError("INVALID_EXPRESSION", "算式包含不支持的内容", 422)

    try:
        result = evaluate(ast.parse(expression, mode="eval"))
    except (SyntaxError, ZeroDivisionError, OverflowError) as exc:
        raise AppError("INVALID_EXPRESSION", "无法计算该算式", 422) from exc
    if not math.isfinite(float(result)) or abs(float(result)) > 1e100:
        raise AppError("EXPRESSION_TOO_LARGE", "计算结果超出允许范围", 422)
    return result


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

    if tool.slug == "calculator":
        expression = str(payload.input.get("expression") or "")
        output = {"expression": expression, "result": evaluate_expression(expression)}
    elif tool.slug == "current-time":
        timezone = str(payload.input.get("timezone") or "Asia/Shanghai")
        try:
            now = datetime.now(ZoneInfo(timezone))
        except ZoneInfoNotFoundError as exc:
            raise AppError("INVALID_TIMEZONE", "时区名称无效", 422) from exc
        output = {
            "timezone": timezone,
            "iso": now.isoformat(),
            "display": now.strftime("%Y-%m-%d %H:%M:%S"),
        }
    else:
        raise AppError("TOOL_NOT_IMPLEMENTED", "该工具暂未配置执行器", 422)

    execution = ToolExecution(
        user_id=user.id,
        tool_id=tool.id,
        message_id=payload.message_id,
        input_data=payload.input,
        output_data=output,
        status="completed",
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)
    return ToolExecuteResponse(execution_id=execution.id, output=output)
