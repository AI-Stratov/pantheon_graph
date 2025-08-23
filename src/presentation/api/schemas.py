from pydantic import BaseModel, Field

from core.constants import ApiStatusEnum


class ApiStatus(BaseModel):
    """Standard API response status model.

    Used for health checks and operation confirmations.
    """

    status: ApiStatusEnum = Field(..., description="Operation status")
    detail: str | None = Field(None, description="Additional status information")


class HealthResponse(BaseModel):
    """Health check response with service status details."""

    status: ApiStatusEnum = Field(..., description="Overall health status")
    services: dict[str, bool] = Field(
        default_factory=dict, description="Individual service health status"
    )
    timestamp: str | None = Field(None, description="Health check timestamp")
