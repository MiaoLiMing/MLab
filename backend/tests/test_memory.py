from sqlalchemy import select

from app.db.session import SessionFactory
from app.models.entities import Memory, User
from app.services.memory import embed_text, relevant_memories


async def test_relevant_memories_rank_matching_content(
    auth_headers: dict[str, str],  # noqa: ARG001
) -> None:
    async with SessionFactory() as db:
        user = await db.scalar(select(User).where(User.email == "tester@example.com"))
        assert user is not None
        db.add_all(
            [
                Memory(
                    user_id=user.id,
                    content="我开发后端时偏好使用 Python 和 FastAPI",
                    category="preference",
                    enabled=True,
                    embedding=embed_text("我开发后端时偏好使用 Python 和 FastAPI"),
                ),
                Memory(
                    user_id=user.id,
                    content="我周末喜欢做川菜",
                    category="preference",
                    enabled=True,
                    embedding=embed_text("我周末喜欢做川菜"),
                ),
            ]
        )
        await db.commit()
        results = await relevant_memories(db, user.id, "Python 后端框架怎么选择")
        assert results[0].content == "我开发后端时偏好使用 Python 和 FastAPI"
