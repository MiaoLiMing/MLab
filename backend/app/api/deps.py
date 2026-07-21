from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.entities import User, UserStatus

bearer = HTTPBearer(auto_error=False)
DBSession = Annotated[AsyncSession, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


async def get_current_user(
    db: DBSession,
    settings: AppSettings,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    if credentials is None:
        raise AppError("NOT_AUTHENTICATED", "请先登录", 401)
    try:
        user_id = decode_access_token(credentials.credentials, settings)
    except (jwt.InvalidTokenError, ValueError):
        raise AppError("INVALID_TOKEN", "登录状态无效或已过期", 401) from None
    user = await db.get(User, user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        raise AppError("INVALID_TOKEN", "登录状态无效或已过期", 401)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
