from uuid import UUID

from fastapi import APIRouter, Response, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.core.errors import NotFoundError
from app.models.entities import Memory
from app.schemas.content import MemoryCreate, MemoryResponse, MemoryUpdate
from app.services.memory import embed_text

router = APIRouter(prefix="/memories", tags=["memories"])


@router.get("", response_model=list[MemoryResponse])
async def list_memories(user: CurrentUser, db: DBSession) -> list[Memory]:
    return list(
        await db.scalars(
            select(Memory).where(Memory.user_id == user.id).order_by(Memory.updated_at.desc())
        )
    )


@router.post("", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
async def create_memory(payload: MemoryCreate, user: CurrentUser, db: DBSession) -> Memory:
    memory = Memory(
        user_id=user.id,
        source_message_id=None,
        embedding=embed_text(payload.content),
        **payload.model_dump(),
    )
    db.add(memory)
    await db.commit()
    await db.refresh(memory)
    return memory


@router.patch("/{memory_id}", response_model=MemoryResponse)
async def update_memory(
    memory_id: UUID, payload: MemoryUpdate, user: CurrentUser, db: DBSession
) -> Memory:
    memory = await db.scalar(
        select(Memory).where(Memory.id == memory_id, Memory.user_id == user.id)
    )
    if memory is None:
        raise NotFoundError("记忆")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(memory, field, value)
    if payload.content is not None:
        memory.embedding = embed_text(payload.content)
    await db.commit()
    await db.refresh(memory)
    return memory


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(memory_id: UUID, user: CurrentUser, db: DBSession) -> Response:
    memory = await db.scalar(
        select(Memory).where(Memory.id == memory_id, Memory.user_id == user.id)
    )
    if memory is None:
        raise NotFoundError("记忆")
    await db.delete(memory)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
