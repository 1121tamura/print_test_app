from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_version: str = "0.1.0"
    api_key: str = Field(alias="API_KEY")
    db_host: str = Field(alias="DB_HOST")
    db_port: int = Field(alias="DB_PORT")
    db_name: str = Field(alias="DB_NAME")
    db_user: str = Field(alias="DB_USER")
    db_password: str = Field(alias="DB_PASSWORD")
    redis_host: str = Field(alias="REDIS_HOST")
    redis_port: int = Field(alias="REDIS_PORT")
    storage_type: str = Field(default="local", alias="STORAGE_TYPE")          # "local" のみ対応（将来拡張用）
    storage_base_dir: str = Field(default="", alias="STORAGE_BASE_DIR")        # PDFのベースディレクトリ（空の場合はkeyをそのまま絶対パスとして扱う）
    pdf_retention_days: int = Field(default=30, alias="PDF_RETENTION_DAYS")    # PDF保管日数（一覧取得の絞り込みに使用）

    model_config = SettingsConfigDict(
        env_file=".env.dev",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
