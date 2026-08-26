"""Application configuration loaded from environment / .env file."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ID-SHIELD"
    app_version: str = "0.1.0"
    app_tagline: str = "Explainable Identity & Document Forensics Platform"

    database_url: str = f"sqlite:///{(BACKEND_DIR / 'data' / 'idshield.db').as_posix()}"
    cors_origins: str = "http://localhost:5173"

    upload_dir: Path = BACKEND_DIR / "data" / "uploads"
    max_upload_mb: int = 10

    face_verification_enabled: bool = False

    log_level: str = "INFO"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
