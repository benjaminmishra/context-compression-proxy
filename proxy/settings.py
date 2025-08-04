from functools import lru_cache
from typing import Dict

from pydantic import BaseSettings, Field, validator


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # Mapping of API token -> username
    user_tokens: Dict[str, str] = Field(default_factory=dict)

    # Simple per-minute request limit per token
    rate_limit_per_minute: int = 60

    # Downstream OpenAI-compatible endpoint
    openai_api_base: str = "https://api.openai.com/v1"
    openai_api_key: str = ""

    @validator("user_tokens", pre=True)
    def parse_user_tokens(cls, v: str | Dict[str, str]) -> Dict[str, str]:
        if isinstance(v, str):
            tokens: Dict[str, str] = {}
            if v:
                for pair in v.split(","):
                    token, user = pair.split(":", 1)
                    tokens[token.strip()] = user.strip()
            return tokens
        return v

    class Config:
        env_prefix = "CCP_"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Cached settings so env vars are parsed only once."""

    return Settings()
