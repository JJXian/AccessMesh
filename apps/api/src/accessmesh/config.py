from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AccessMesh"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+asyncpg://accessmesh:accessmesh@localhost:5432/accessmesh"
    opa_url: str = "http://localhost:8181"
    opa_decision_path: str = "/v1/data/accessmesh/decision"
    demo_identity_enabled: bool = True
    default_demo_subject_id: str = "user-requester"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])


@lru_cache
def get_settings() -> Settings:
    return Settings()
