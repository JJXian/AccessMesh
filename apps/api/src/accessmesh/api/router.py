from fastapi import APIRouter

from accessmesh.api.routes import access_requests, demo, health, resources

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(demo.router, prefix="/demo", tags=["demo"])
api_router.include_router(resources.router, prefix="/resources", tags=["resources"])
api_router.include_router(
    access_requests.router,
    prefix="/access-requests",
    tags=["access-requests"],
)
