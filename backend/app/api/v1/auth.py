from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, status
from sqlalchemy import select

from app.api.deps import AppSettings, CurrentUser, DBSession
from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.entities import RefreshToken, User
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.schemas.common import MessageResponse

router = APIRouter(prefix="/auth", tags=["auth"])


async def issue_tokens(user: User, db: DBSession, settings: AppSettings) -> TokenResponse:
    access_token, access_expires_at = create_access_token(user.id, settings)
    refresh_token, refresh_hash = create_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=datetime.now(UTC) + timedelta(days=settings.jwt_refresh_expire_days),
            revoked_at=None,
            created_at=datetime.now(UTC),
        )
    )
    await db.commit()
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        access_expires_at=access_expires_at,
        user=UserResponse.model_validate(user),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: DBSession, settings: AppSettings) -> TokenResponse:
    email = payload.email.lower()
    existing = await db.scalar(select(User).where(User.email == email))
    if existing:
        raise AppError("EMAIL_ALREADY_EXISTS", "该邮箱已注册", 409)
    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name.strip(),
        avatar_url=None,
    )
    db.add(user)
    await db.flush()
    return await issue_tokens(user, db, settings)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: DBSession, settings: AppSettings) -> TokenResponse:
    user = await db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise AppError("INVALID_CREDENTIALS", "邮箱或密码错误", 401)
    return await issue_tokens(user, db, settings)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, db: DBSession, settings: AppSettings) -> TokenResponse:
    record = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(payload.refresh_token))
    )
    now = datetime.now(UTC)
    expires_at = record.expires_at if record else now
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if record is None or record.revoked_at is not None or expires_at < now:
        raise AppError("INVALID_REFRESH_TOKEN", "刷新凭据无效或已过期", 401)
    user = await db.get(User, record.user_id)
    if user is None:
        raise AppError("INVALID_REFRESH_TOKEN", "刷新凭据无效或已过期", 401)
    record.revoked_at = now
    await db.flush()
    return await issue_tokens(user, db, settings)


@router.post("/logout", response_model=MessageResponse)
async def logout(payload: LogoutRequest, db: DBSession) -> MessageResponse:
    record = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_token(payload.refresh_token))
    )
    if record and record.revoked_at is None:
        record.revoked_at = datetime.now(UTC)
        await db.commit()
    return MessageResponse(message="已退出登录")


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(user)
