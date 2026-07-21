import ast
import math
import operator
from datetime import datetime
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.entities import ToolDefinition, ToolExecution

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


def run_builtin_tool(tool: ToolDefinition, input_data: dict[str, Any]) -> dict[str, Any]:
    if tool.slug == "calculator":
        expression = str(input_data.get("expression") or "")
        return {"expression": expression, "result": evaluate_expression(expression)}
    if tool.slug == "current-time":
        timezone = str(input_data.get("timezone") or "Asia/Shanghai")
        try:
            now = datetime.now(ZoneInfo(timezone))
        except ZoneInfoNotFoundError as exc:
            raise AppError("INVALID_TIMEZONE", "时区名称无效", 422) from exc
        return {
            "timezone": timezone,
            "iso": now.isoformat(),
            "display": now.strftime("%Y-%m-%d %H:%M:%S"),
        }
    raise AppError("TOOL_NOT_IMPLEMENTED", "该工具暂未配置执行器", 422)


async def record_tool_execution(
    db: AsyncSession,
    user_id: UUID,
    tool: ToolDefinition,
    input_data: dict[str, Any],
    output_data: dict[str, Any],
    message_id: UUID | None,
) -> ToolExecution:
    execution = ToolExecution(
        user_id=user_id,
        tool_id=tool.id,
        message_id=message_id,
        input_data=input_data,
        output_data=output_data,
        status="completed",
    )
    db.add(execution)
    await db.flush()
    return execution
