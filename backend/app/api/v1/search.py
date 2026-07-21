from fastapi import APIRouter, Query
from sqlalchemy import or_, select

from app.api.deps import CurrentUser, DBSession
from app.models.entities import Conversation, Document, Resource, Task, Visibility
from app.schemas.content import SearchResult

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=list[SearchResult])
async def global_search(
    user: CurrentUser, db: DBSession, q: str = Query(min_length=1, max_length=100)
) -> list[SearchResult]:
    term = f"%{q.strip()}%"
    results: list[SearchResult] = []
    conversations = await db.scalars(
        select(Conversation)
        .where(Conversation.user_id == user.id, Conversation.title.ilike(term))
        .limit(8)
    )
    results.extend(
        SearchResult(
            id=item.id,
            result_type="conversation",
            title=item.title,
            snippet="历史对话",
            path=f"/chat/{item.id}",
        )
        for item in conversations
    )
    tasks = await db.scalars(
        select(Task)
        .where(Task.user_id == user.id, or_(Task.title.ilike(term), Task.content.ilike(term)))
        .limit(8)
    )
    results.extend(
        SearchResult(
            id=item.id,
            result_type="task",
            title=item.title,
            snippet=item.content[:120],
            path="/tasks",
        )
        for item in tasks
    )
    documents = await db.scalars(
        select(Document)
        .where(
            Document.user_id == user.id,
            or_(Document.title.ilike(term), Document.content_text.ilike(term)),
        )
        .limit(8)
    )
    results.extend(
        SearchResult(
            id=item.id,
            result_type="document",
            title=item.title,
            snippet=item.content_text[:120],
            path="/documents",
        )
        for item in documents
    )
    resources = await db.scalars(
        select(Resource)
        .where(
            or_(
                Resource.owner_id == user.id,
                Resource.visibility.in_([Visibility.PUBLIC, Visibility.SYSTEM]),
            ),
            or_(Resource.title.ilike(term), Resource.description.ilike(term)),
        )
        .limit(8)
    )
    results.extend(
        SearchResult(
            id=item.id,
            result_type="resource",
            title=item.title,
            snippet=item.description,
            path="/resources",
        )
        for item in resources
    )
    return results[:30]
