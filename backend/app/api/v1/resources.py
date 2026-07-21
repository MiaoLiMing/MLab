from uuid import UUID

from fastapi import APIRouter, Response, status
from sqlalchemy import or_, select

from app.api.deps import CurrentUser, DBSession
from app.core.errors import NotFoundError
from app.models.entities import Resource, Visibility
from app.schemas.content import ResourceCreate, ResourceResponse

router = APIRouter(prefix="/resources", tags=["resources"])


@router.get("", response_model=list[ResourceResponse])
async def list_resources(user: CurrentUser, db: DBSession, q: str | None = None) -> list[Resource]:
    query = select(Resource).where(
        or_(
            Resource.owner_id == user.id,
            Resource.visibility.in_([Visibility.PUBLIC, Visibility.SYSTEM]),
        )
    )
    if q:
        term = f"%{q.strip()}%"
        query = query.where(or_(Resource.title.ilike(term), Resource.description.ilike(term)))
    return list(await db.scalars(query.order_by(Resource.updated_at.desc())))


@router.post("", response_model=ResourceResponse, status_code=status.HTTP_201_CREATED)
async def create_resource(payload: ResourceCreate, user: CurrentUser, db: DBSession) -> Resource:
    resource = Resource(owner_id=user.id, visibility=Visibility.PRIVATE, **payload.model_dump())
    db.add(resource)
    await db.commit()
    await db.refresh(resource)
    return resource


@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(resource_id: UUID, user: CurrentUser, db: DBSession) -> Response:
    resource = await db.scalar(
        select(Resource).where(Resource.id == resource_id, Resource.owner_id == user.id)
    )
    if resource is None:
        raise NotFoundError("资源")
    await db.delete(resource)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
