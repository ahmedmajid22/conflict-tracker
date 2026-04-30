from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # ── Supabase ─────────────────────────────────────────
    supabase_url: str = ""
    supabase_key: str = ""

    # ── Upstash Redis ────────────────────────────────────
    upstash_redis_rest_url:   str = ""
    upstash_redis_rest_token: str = ""

    # ── App settings ─────────────────────────────────────
    app_name:    str = "Conflict Tracker API"
    app_version: str = "1.0.0"
    log_level:   str = "INFO"
    debug:       bool = False

    # ── CORS ─────────────────────────────────────────────
    # Comma-separated list of allowed origins.
    # In production, set this to your Flutter web domain.
    # "*" allows all origins (fine for open data APIs).
    allowed_origins: str = "*"

    # ── Cache TTLs (seconds) ─────────────────────────────
    cache_ttl_events:     int = 120   # 2 minutes — events change frequently
    cache_ttl_map:        int = 300   # 5 minutes — map data changes less often
    cache_ttl_analytics:  int = 600   # 10 minutes — aggregates are slow to change
    cache_ttl_health:     int = 30    # 30 seconds — health should be fresh

    # ── Pagination ───────────────────────────────────────
    max_page_size: int = 200

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins(self) -> list[str]:
        if self.allowed_origins == "*":
            return ["*"]
        return [o.strip() for o in self.allowed_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.
    The @lru_cache means this is only computed once per process.
    """
    return Settings()