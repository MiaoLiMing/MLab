from typing import Any


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


class NotFoundError(AppError):
    def __init__(self, resource: str = "资源") -> None:
        super().__init__("NOT_FOUND", f"{resource}不存在", 404)


class ForbiddenError(AppError):
    def __init__(self, message: str = "无权执行此操作") -> None:
        super().__init__("FORBIDDEN", message, 403)
