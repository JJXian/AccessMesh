"""应用配置定义及配置实例的缓存入口。"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """统一管理可由环境变量覆盖的运行时配置。"""

    # 忽略未声明的环境变量，避免部署环境中的无关配置导致应用启动失败。
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
    llm_enabled: bool = False
    llm_provider: str = "deepseek"
    llm_base_url: str = "https://api.deepseek.com"
    llm_api_key: SecretStr = SecretStr("")
    llm_model: str = "deepseek-v4-flash"
    llm_response_format: Literal["json_object", "json_schema"] = "json_object"
    llm_max_tokens: int = Field(default=1024, ge=128, le=8192)
    llm_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    llm_max_retries: int = Field(default=2, ge=0, le=5)
    llm_trust_env: bool = False


@lru_cache
def get_settings() -> Settings:
    """返回进程内复用的配置实例，避免重复解析环境变量和 .env 文件。"""

    return Settings()
