from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    secret_key: str = Field(min_length=16)
    database_url: str = ""
    data_dir: Path = Path("data")
    sheet_id: str = Field(min_length=1)
    admin_username: str = "admin"
    admin_password: str = Field(min_length=4)
    sheet_cache_seconds: int = 300
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"

    @property
    def pdf_dir(self) -> Path:
        return self.data_dir / "pdfs"

    @property
    def signature_dir(self) -> Path:
        return self.data_dir / "signatures"

    @property
    def branding_dir(self) -> Path:
        return self.data_dir / "branding"

    @property
    def sqlalchemy_url(self) -> str:
        if self.database_url.strip():
            return self.database_url
        db_file = (self.data_dir / "app.db").resolve().as_posix()
        return f"sqlite:///{db_file}"


settings = Settings()
