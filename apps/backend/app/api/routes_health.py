from fastapi import APIRouter

from app.schemas.status import HealthResponse

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Kiểm tra sức khỏe backend. AI worker/camera chưa được nối nên trả False."""
    return HealthResponse(status="ok", ai_worker_alive=False, camera_connected=False)
