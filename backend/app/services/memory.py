import hashlib
import math
import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Memory

EMBEDDING_DIMENSIONS = 256


def embed_text(text: str) -> list[float]:
    """Create a deterministic lexical vector locally, without sending memory to another API."""

    normalized = text.lower().strip()
    words = re.findall(r"[a-z0-9_]+", normalized)
    cjk = [char for char in normalized if "\u3400" <= char <= "\u9fff"]
    cjk_bigrams = ["".join(cjk[index : index + 2]) for index in range(len(cjk) - 1)]
    tokens = [*words, *cjk, *cjk_bigrams]
    vector = [0.0] * EMBEDDING_DIMENSIONS
    for token in tokens:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        index = int.from_bytes(digest[:4], "big") % EMBEDDING_DIMENSIONS
        sign = 1.0 if digest[4] & 1 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector))
    if norm:
        return [value / norm for value in vector]
    return vector


def cosine_similarity(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=False))


async def relevant_memories(
    db: AsyncSession, user_id: UUID, query: str, limit: int = 6
) -> list[Memory]:
    query_vector = embed_text(query)
    dialect = db.bind.dialect.name if db.bind else "unknown"
    if dialect == "postgresql":
        result = await db.scalars(
            select(Memory)
            .where(
                Memory.user_id == user_id,
                Memory.enabled.is_(True),
                Memory.embedding.is_not(None),
            )
            .order_by(Memory.embedding.cosine_distance(query_vector))
            .limit(limit)
        )
        items = list(result)
        if items:
            return items

    candidates = list(
        await db.scalars(
            select(Memory)
            .where(Memory.user_id == user_id, Memory.enabled.is_(True))
            .order_by(Memory.updated_at.desc())
            .limit(100)
        )
    )
    for memory in candidates:
        if memory.embedding is None:
            memory.embedding = embed_text(memory.content)
    candidates.sort(
        key=lambda item: cosine_similarity(item.embedding or [], query_vector), reverse=True
    )
    return candidates[:limit]
