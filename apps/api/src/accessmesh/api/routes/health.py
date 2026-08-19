"""服务健康检查接口。"""

from fastapi import APIRouter

from accessmesh import __version__
from accessmesh.config import get_settings
from accessmesh.domain.schemas import HealthRead

router = APIRouter()


@router.get("/health", response_model=HealthRead)
async def health() -> HealthRead:
    """返回服务名、版本和基础存活状态。"""

    settings = get_settings()
    return HealthRead(status="ok", service=settings.app_name, version=__version__)
