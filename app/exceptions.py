from fastapi import HTTPException, status


class BaseAPIException(HTTPException):
    """Base class for API exceptions with consistent formatting."""
    def __init__(self, status_code: int, error_code: str, message: str, details: dict | None = None):
        super().__init__(
            status_code=status_code,
            detail={
                "error": {
                    "code": error_code,
                    "message": message,
                    "details": details or {}
                }
            }
        )


class TaskNotFoundException(BaseAPIException):
    def __init__(self, task_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="TASK_NOT_FOUND",
            message=f"Task with id {task_id} not found",
            details={"task_id": task_id}
        )


class ValidationException(BaseAPIException):
    def __init__(self, message: str, field: str | None = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            message=message,
            details={"field": field} if field else {}
        )


class DatabaseException(BaseAPIException):
    def __init__(self, message: str = "Database operation failed"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DATABASE_ERROR",
            message=message
        )