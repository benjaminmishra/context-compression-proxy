from functools import lru_cache
from typing import Dict

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # Raw mapping provided via env var, e.g. "token:user,token2:user2"
    user_tokens_raw: str = Field("", env="CCP_USER_TOKENS")

    # Simple per-minute request limit per token
    rate_limit_per_minute: int = 60

    # Downstream OpenAI-compatible endpoint
    openai_api_base: str = "https://api.openai.com/v1"
    openai_api_key: str = ""

    @property
    def user_tokens(self) -> Dict[str, str]:
        tokens: Dict[str, str] = {}
        if self.user_tokens_raw:
            for pair in self.user_tokens_raw.split(","):
                token, user = pair.split(":", 1)
                tokens[token.strip()] = user.strip()
        return tokens

    class Config:
        env_prefix = "CCP_"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Cached settings so env vars are parsed only once."""

    return Settings()
