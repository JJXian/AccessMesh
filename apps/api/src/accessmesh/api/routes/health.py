from fastapi import APIRouter

from accessmesh import __version__
from accessmesh.config import get_settings
from accessmesh.domain.schemas import HealthRead

router = APIRouter()


@router.get("/health", response_model=HealthRead)
async def health() -> HealthRead:
    settings = get_settings()
    return HealthRead(status="ok", service=settings.app_name, version=__version__)
