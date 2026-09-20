from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://lifeos:lifeos@db:5432/lifeos"
    #: Baglanti havuzu. Tek kullanicili local-first kurulumda 15+20 baglanti
    #: bosa duran bir kaynaktir; kucuk varsayilan yeter. API ve worker ayni
    #: ayarlari kullanir (worker icin ayri engine acmak bu olcekte gereksiz).
    db_pool_size: int = 5
    db_max_overflow: int = 5
    extension_id: str = ""
    #: Gun siniri (emek haritasi, gunluk ozet) bu bolgeye gore hesaplanir.
    #: Container UTC kosuyor -- burasi kullanicinin yasadigi bolge olmali.
    timezone: str = "Europe/Istanbul"
    rss_default_interval_minutes: int = 60
    rss_retention_days: int = 90
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://127.0.0.1:8787/api/auth/google/callback"
    worker_enabled: bool = False

    @property
    def cors_origins(self) -> list[str]:
        origins = ["http://127.0.0.1:5173", "http://localhost:5173"]
        if self.extension_id:
            origins.append(f"chrome-extension://{self.extension_id}")
        return origins


settings = Settings()
