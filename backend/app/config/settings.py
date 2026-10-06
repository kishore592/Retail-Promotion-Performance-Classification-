from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_env: str = "development"
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.6-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    database_url: str = "sqlite+aiosqlite:///./retail.db"
    chroma_persist_dir: str = "./chroma"
    max_retries: int = 2
    high_risk_threshold: float = 0.65
    review_capacity: float = 0.20
    cors_origins: str = "http://localhost:3000"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
