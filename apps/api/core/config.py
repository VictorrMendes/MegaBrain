from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    env: str = "development"
    log_level: str = "INFO"

    # Database
    database_url: str = "postgresql+asyncpg://paios:paios@localhost:5432/paios"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_default_model: str = "qwen3:8b"
    ollama_embedding_model: str = "nomic-embed-text"

    # Notifications
    ntfy_url: str = "http://localhost:2586"
    ntfy_topic: str = "paios"

    # Observability
    influxdb_url: str = "http://localhost:8086"
    influxdb_token: str = ""
    influxdb_org: str = "vmserver"
    influxdb_bucket: str = "paios"

    # Auth
    secret_key: str = "changeme"
    access_token_expire_minutes: int = 60


settings = Settings()
