# -*- coding: utf-8 -*-
"""应用配置（pydantic-settings）"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "dev"
    app_name: str = "BLACK ERP"
    secret_key: str = "dev-secret-change-me"
    session_ttl_seconds: int = 43_200
    secure_cookie: bool = False

    database_url: str = "mysql+asyncmy://erp:erp_dev_2026@127.0.0.1:3306/black_erp?charset=utf8mb4"
    redis_url: str = "redis://127.0.0.1:6379/0"
    celery_broker_url: str = "redis://127.0.0.1:6379/0"

    upload_root: str = "./data/uploads"
    max_upload_mb: int = 50
    ocr_provider: str = "none"

    @property
    def upload_path(self) -> Path:
        p = Path(self.upload_root)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def is_dev(self) -> bool:
        return self.app_env == "dev"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
