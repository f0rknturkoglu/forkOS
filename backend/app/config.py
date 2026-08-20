from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://lifeos:lifeos@db:5432/lifeos"
    extension_id: str = ""
    rss_default_interval_minutes: int = 30
    rss_retention_days: int = 90

    @property
    def cors_origins(self) -> list[str]:
        origins = ["http://127.0.0.1:5173", "http://localhost:5173"]
        if self.extension_id:
            origins.append(f"chrome-extension://{self.extension_id}")
        return origins


settings = Settings()
