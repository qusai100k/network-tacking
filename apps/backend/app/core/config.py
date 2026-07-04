from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NetVision AI Backend"
    database_url: str = "sqlite+aiosqlite:///./netvision_ai.db"
    refresh_interval_seconds: float = 2.0
    public_ip_timeout_seconds: float = 3.0
    history_limit: int = 60

    default_ai_provider: str = "ollama"
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-1.5-flash"
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-sonnet-4-6"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.1"
    ai_request_timeout_seconds: float = 20.0

    model_config = SettingsConfigDict(
        env_prefix="NETVISION_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()