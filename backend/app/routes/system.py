import sys
from fastapi import APIRouter
from ..models import SystemStatusResponse
from ..config import get_active_mode, get_configured_provider, DB_PATH
from ..database import get_db

router = APIRouter(prefix="/api/system", tags=["System"])

@router.get("/status", response_model=SystemStatusResponse)
def get_system_status():
    total_sessions = 0
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as cnt FROM sessions")
            row = cursor.fetchone()
            total_sessions = row["cnt"] if row else 0
    except Exception:
        total_sessions = 0

    return SystemStatusResponse(
        product_name="codewise",
        tagline="understand the code. master the logic.",
        status="healthy",
        active_mode=get_active_mode(),
        configured_provider=get_configured_provider(),
        database_path=str(DB_PATH),
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        total_sessions=total_sessions
    )
