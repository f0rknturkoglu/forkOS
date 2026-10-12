from pathlib import Path
from typing import Literal

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
    # Dedicated Hermes profile only; credentials never leave the backend.
    hermes_goal_base_url: str = "http://127.0.0.1:8643"
    hermes_goal_api_key: str = ""
    hermes_goal_profile_config: str = ""
    hermes_goal_topology: Literal["native", "host_bridge"] = "native"
    hermes_goal_model_api_key: str = ""

    #: Opsiyonel Obsidian Vault destegi (hibrit mimari).
    #: Bos birakilirsa Vault entegrasyonu pasiftir ve forkOS normal calisir.
    obsidian_vault_path: str = ""
    obsidian_vault_name: str = ""

    #: H4 yerel bilis (local cognition) router'i.
    #:
    #: Varsayilan KAPALI: yerel model kurulu olmayabilir ve H4 zorunlu bir
    #: bagimlilik DEGILDIR. Kapaliyken arac yuzeyde kalir ve `H4_DISABLED`
    #: doner (MCP arac sayisi yapilandirmaya gore DEGISMEZ).
    h4_enabled: bool = False
    #: Yalnizca loopback kabul edilir (localhost / 127.0.0.1 / ::1). Baska bir
    #: host `INVALID_LOCAL_MODEL_ENDPOINT` ile reddedilir: H4 yanlislikla bir
    #: bulut gecidine donusemez.
    h4_ollama_base_url: str = "http://127.0.0.1:11434"
    #: Model kimlikleri YAPILANDIRMADAN gelir; kodda sabit model adi YOKTUR.
    #: Bos = o slot yapilandirilmamis.
    h4_small_model: str = ""
    h4_medium_model: str = ""
    #: Girdi karakter butceleri YONLENDIRME guvenlik sinirlaridir; modelin
    #: gercek baglam penceresi degildir (daha buyuk olabilir).
    h4_small_input_chars: int = 12000
    h4_medium_input_chars: int = 24000
    h4_timeout_seconds: float = 45.0
    #: A3 epizodik damıtma bütçesi (saniye).
    #:
    #: `post_llm_call` kullanıcıya dönük turun hemen yanındadır, bu yüzden
    #: H4'ün 45 sn'lik varsayılanı bu yol için KABUL EDİLEMEZ. Ölçüm (yerel
    #: qwen2.5:14b-instruct-q4_K_M, episodic_turn_v1): 15.3–16.5 sn/model
    #: çağrısı. Bu bütçe aşılırsa A3 `EPISODE_EXTRACTION_TIMEOUT` ile degrade
    #: eder ve uydurma yapmaz; devir yine metadata + H5 gözlemleriyle mühürlenir.
    #: Konuşmaya özgü ifade isteniyorsa H4'ü KÜÇÜK bir yerel modele yönlendirin.
    a3_extraction_budget_seconds: float = 2.0

    # A5.1: opt-in local context reranking. No daemon is started by forkOS.
    a5_context_mode: Literal["off", "shadow", "assist", "on"] = "off"
    a5_jevmlx_base_url: str = "http://127.0.0.1:8000"
    a5_context_timeout_seconds: float = 1.5
    # Only canonical container wiring may opt into the Docker Desktop host bridge.
    a5_host_bridge_enabled: bool = False

    # A5.2: independent, opt-in local Memory Judge. The default API image does
    # not include poorjev or an NLI model; OFF never imports either one.
    a5_memory_mode: Literal["off", "shadow", "assist", "on"] = "off"
    a5_memory_provider: Literal["poorjev"] = "poorjev"
    a5_memory_model_path: str = ""
    a5_memory_timeout_seconds: float = 20.0

    # A5.3: independent, opt-in local Answer Evidence Judge.
    a5_answer_mode: Literal["off", "shadow", "assist", "on"] = "off"
    a5_answer_provider: Literal["poorjev"] = "poorjev"
    a5_answer_model_path: str = ""
    a5_answer_timeout_seconds: float = 20.0

    # career-ops capability engine integration (C1/C2)
    career_ops_enabled: bool = False
    career_ops_root: str = ""
    career_ops_node_bin: str = "node"
    career_ops_timeout_seconds: float = 30.0
    career_ops_max_buffer_bytes: int = 512 * 1024
    career_ops_runtime_dir: str = ""
    career_ops_discovery_enabled: bool = True
    career_ops_discovery_timeout_seconds: float = 300.0
    career_ops_discovery_since_days: int = 30
    # Pinned scan-ats-full --limit is a per-ATS company/tenant cap, not a job cap.
    career_ops_discovery_limit: int = 500
    career_ops_discovery_max_buffer_bytes: int = 16 * 1024 * 1024

    # Career Reasoner provider abstraction (C4/C5)
    career_reasoner_provider: Literal["none", "ollama", "openai", "gemini", "openrouter"] = "none"
    career_reasoner_model: str = ""
    career_reasoner_base_url: str = ""
    career_reasoner_api_key: str = ""
    career_reasoner_timeout_seconds: float = 60.0
    career_reasoner_temperature: float = 0.1

    @property
    def resolved_career_ops_root(self) -> Path:
        if self.career_ops_root and self.career_ops_root.strip():
            return Path(self.career_ops_root.strip()).expanduser().resolve()
        repo_root = Path(__file__).resolve().parent.parent.parent
        return (repo_root / ".vendor" / "career-ops").resolve()

    @property
    def resolved_career_ops_runtime_dir(self) -> Path:
        if self.career_ops_runtime_dir and self.career_ops_runtime_dir.strip():
            return Path(self.career_ops_runtime_dir.strip()).expanduser().resolve()
        repo_root = Path(__file__).resolve().parent.parent.parent
        return (repo_root / "backend" / "data" / "runtime" / "career-ops").resolve()

    @property
    def resolved_obsidian_vault_path(self) -> Path | None:
        if not self.obsidian_vault_path or not self.obsidian_vault_path.strip():
            return None
        return Path(self.obsidian_vault_path.strip()).expanduser().resolve()

    @property
    def resolved_obsidian_vault_name(self) -> str:
        if self.obsidian_vault_name and self.obsidian_vault_name.strip():
            return self.obsidian_vault_name.strip()
        path = self.resolved_obsidian_vault_path
        if path:
            return path.name
        return "Vault"

    @property
    def cors_origins(self) -> list[str]:
        origins = ["http://127.0.0.1:5173", "http://localhost:5173"]
        if self.extension_id:
            origins.append(f"chrome-extension://{self.extension_id}")
        return origins


settings = Settings()
