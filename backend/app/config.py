from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "AI SQL Agent"
    app_version: str = "0.2.0"
    debug: bool = False

    # AI Service
    anthropic_api_key: str = ""
    ai_enabled: bool = True
    ai_model: str = "claude-sonnet-4-6"
    ai_base_url: str = ""
    ai_max_tokens: int = 100000


settings = Settings()
