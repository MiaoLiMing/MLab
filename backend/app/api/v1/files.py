import hashlib
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, File, Response, UploadFile, status
from fastapi.responses import FileResponse as DownloadResponse
from sqlalchemy import select

from app.api.deps import AppSettings, CurrentUser, DBSession
from app.core.errors import AppError, NotFoundError
from app.models.entities import FileAsset
from app.schemas.content import FileResponse

router = APIRouter(prefix="/files", tags=["files"])

ALLOWED_MIME_TYPES = {
    "text/plain",
    "text/markdown",
    "application/pdf",
    "application/json",
    "image/jpeg",
    "image/png",
    "image/webp",
}


@router.get("", response_model=list[FileResponse])
async def list_files(user: CurrentUser, db: DBSession) -> list[FileAsset]:
    return list(
        await db.scalars(
            select(FileAsset)
            .where(FileAsset.user_id == user.id)
            .order_by(FileAsset.created_at.desc())
        )
    )


@router.post("", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    user: CurrentUser,
    db: DBSession,
    settings: AppSettings,
    upload: Annotated[UploadFile, File(...)],
) -> FileAsset:
    content_type = upload.content_type or "application/octet-stream"
    if content_type not in ALLOWED_MIME_TYPES:
        raise AppError("UNSUPPORTED_FILE_TYPE", "不支持该文件类型", 415)
    max_size = settings.max_upload_size_mb * 1024 * 1024
    digest = hashlib.sha256()
    size = 0
    extension = Path(upload.filename or "file").suffix.lower()[:10]
    storage_key = f"{user.id}/{uuid4().hex}{extension}"
    target = settings.local_storage_path / storage_key
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("wb") as output:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > max_size:
                    raise AppError(
                        "FILE_TOO_LARGE", f"文件不能超过 {settings.max_upload_size_mb}MB", 413
                    )
                digest.update(chunk)
                output.write(chunk)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    asset = FileAsset(
        user_id=user.id,
        original_name=(upload.filename or "file")[:255],
        storage_key=storage_key,
        mime_type=content_type,
        size=size,
        sha256=digest.hexdigest(),
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return asset


@router.get("/{file_id}/content")
async def download_file(
    file_id: UUID, user: CurrentUser, db: DBSession, settings: AppSettings
) -> DownloadResponse:
    asset = await db.scalar(
        select(FileAsset).where(FileAsset.id == file_id, FileAsset.user_id == user.id)
    )
    if asset is None:
        raise NotFoundError("文件")
    path = settings.local_storage_path / asset.storage_key
    if not path.exists():
        raise NotFoundError("文件内容")
    return DownloadResponse(path, media_type=asset.mime_type, filename=asset.original_name)


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: UUID, user: CurrentUser, db: DBSession, settings: AppSettings
) -> Response:
    asset = await db.scalar(
        select(FileAsset).where(FileAsset.id == file_id, FileAsset.user_id == user.id)
    )
    if asset is None:
        raise NotFoundError("文件")
    path = settings.local_storage_path / asset.storage_key
    path.unlink(missing_ok=True)
    await db.delete(asset)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
