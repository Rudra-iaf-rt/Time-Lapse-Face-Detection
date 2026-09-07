# api/schemas/response.py
from typing import Any, Optional, Generic, TypeVar
from datetime import datetime
from pydantic import BaseModel, Field

T = TypeVar("T")


class ResponseModel(BaseModel):
    """Standard success envelope."""

    success: bool = True
    message: Optional[str] = None
    data: Optional[Any] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """Standard error envelope."""

    error: str
    status_code: int
    detail: Optional[Any] = None
    timestamp: str


class HealthDependencyStatus(BaseModel):
    """Single dependency health status."""

    status: str
    detail: Optional[str] = None


class ReadyResponse(BaseModel):
    """Readiness probe response."""

    status: str
    dependencies: dict
    timestamp: datetime = Field(default_factory=datetime.utcnow)
