from pathlib import Path
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    session_secret: str = Field(min_length=16)
    login_username: str = Field(min_length=1)
    login_password: str = Field(min_length=1)

    workspace_dir: Path
    excel_path: Path
    excel_backup_dir: Path

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def db_path(self) -> Path:
        return self.workspace_dir / "index.sqlite"

    @property
    def review_status_path(self) -> Path:
        return self.workspace_dir / "review_status.json"

    @property
    def master_path(self) -> Path:
        return self.workspace_dir / "master" / "master.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
