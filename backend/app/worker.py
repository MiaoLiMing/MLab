import re
from uuid import UUID

from arq.connections import RedisSettings
from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionFactory
from app.models.entities import Memory, User

MEMORY_TRIGGERS = ("记住", "我喜欢", "我偏好", "我的习惯", "以后请", "我不喜欢")
SENSITIVE_PATTERN = re.compile(r"(密码|口令|api\s*key|secret|身份证|银行卡|信用卡)", re.IGNORECASE)


async def extract_memory(_: dict[str, object], user_id: str, content: str) -> None:
    text = " ".join(content.strip().split())[:1000]
    if not text or not any(trigger in text for trigger in MEMORY_TRIGGERS):
        return
    if SENSITIVE_PATTERN.search(text):
        return
    async with SessionFactory() as db:
        user = await db.get(User, UUID(user_id))
        if user is None or not user.memory_enabled:
            return
        existing = await db.scalar(
            select(Memory.id).where(Memory.user_id == user.id, Memory.content == text)
        )
        if existing is not None:
            return
        db.add(Memory(user_id=user.id, source_message_id=None, content=text, category="preference"))
        await db.commit()


class WorkerSettings:
    functions = [extract_memory]
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = 10
    job_timeout = 30
