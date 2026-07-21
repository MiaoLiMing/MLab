from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Response, status
from sqlalchemy import select

from app.api.deps import AppSettings, CurrentUser, DBSession
from app.core.errors import NotFoundError
from app.models.entities import Task, TaskTemplate
from app.schemas.content import (
    AITextResponse,
    TaskAIRequest,
    TaskCreate,
    TaskResponse,
    TaskTemplateResponse,
    TaskUpdate,
)
from app.services.completion import complete_text

router = APIRouter(tags=["tasks"])


@router.get("/task-templates", response_model=list[TaskTemplateResponse])
async def list_templates(db: DBSession) -> list[TaskTemplate]:
    return list(await db.scalars(select(TaskTemplate).order_by(TaskTemplate.created_at)))


@router.get("/tasks", response_model=list[TaskResponse])
async def list_tasks(
    user: CurrentUser, db: DBSession, task_status: str | None = None
) -> list[Task]:
    query = select(Task).where(Task.user_id == user.id)
    if task_status:
        query = query.where(Task.status == task_status)
    return list(await db.scalars(query.order_by(Task.created_at.desc())))


@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(payload: TaskCreate, user: CurrentUser, db: DBSession) -> Task:
    task = Task(user_id=user.id, **payload.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(task_id: UUID, payload: TaskUpdate, user: CurrentUser, db: DBSession) -> Task:
    task = await db.scalar(select(Task).where(Task.id == task_id, Task.user_id == user.id))
    if task is None:
        raise NotFoundError("任务")
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("status") == "done" and task.status != "done":
        task.completed_at = datetime.now(UTC)
    elif changes.get("status") and changes["status"] != "done":
        task.completed_at = None
    for field, value in changes.items():
        setattr(task, field, value)
    await db.commit()
    await db.refresh(task)
    return task


@router.post("/tasks/{task_id}/ai-breakdown", response_model=AITextResponse)
async def break_down_task(
    task_id: UUID,
    payload: TaskAIRequest,
    user: CurrentUser,
    db: DBSession,
    settings: AppSettings,
) -> AITextResponse:
    task = await db.scalar(select(Task).where(Task.id == task_id, Task.user_id == user.id))
    if task is None:
        raise NotFoundError("任务")
    prompt = (
        f"任务：{task.title}\n现有说明：{task.content or '无'}\n"
        f"补充要求：{payload.instruction or '无'}"
    )
    content = await complete_text(
        db,
        settings,
        user.id,
        prompt,
        system_prompt=(
            "你是执行计划助手。把任务拆成有顺序、可验收的步骤，指出依赖和风险，"
            "使用简洁的 Markdown 清单。"
        ),
        model_config_id=payload.model_config_id,
    )
    task.content = content
    await db.commit()
    return AITextResponse(content=content)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: UUID, user: CurrentUser, db: DBSession) -> Response:
    task = await db.scalar(select(Task).where(Task.id == task_id, Task.user_id == user.id))
    if task is None:
        raise NotFoundError("任务")
    await db.delete(task)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
