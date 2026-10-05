from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Phản hồi của GET /api/v1/health."""

    status: str
    ai_worker_alive: bool
    camera_connected: bool
