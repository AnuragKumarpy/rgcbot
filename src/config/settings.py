from typing import List, Literal, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Bot API Token — no default. Must come from .env (BOT_TOKEN=...).
    # A hardcoded placeholder here previously meant a missing .env value
    # would silently start the bot with a fake token instead of failing
    # with a clear error.
    bot_token: str

    # Mode: polling or webhook
    bot_mode: Literal["polling", "webhook"] = Field(default="webhook")

    # Webhook server configuration
    # webhook_host has no default either — the ngrok URL baked in here
    # previously meant a production deploy with a missing .env value would
    # silently try to register a webhook against a dead ngrok tunnel
    # instead of erroring immediately. Only used when bot_mode="webhook".
    webhook_host: str = Field(default="")
    webhook_path: str = Field(default="/webhook")
    webhook_secret: Optional[str] = Field(default=None)
    server_host: str = Field(default="0.0.0.0")
    server_port: int = Field(default=8000)

    # Super Admins
    bot_super_admins: List[int] = Field(default_factory=list)

    @field_validator("bot_super_admins", mode="before")
    @classmethod
    def parse_super_admins(cls, v):
        if isinstance(v, int):
            return [v]
        if isinstance(v, str):
            if not v.strip():
                return []
            return [int(x.strip()) for x in v.split(",") if x.strip().isdigit()]
        if isinstance(v, (list, tuple, set)):
            return [int(x) for x in v if str(x).isdigit() or isinstance(x, int)]
        return v or []

    @field_validator("webhook_host")
    @classmethod
    def require_webhook_host_in_webhook_mode(cls, v, info):
        # bot_mode may not be validated yet depending on field order, so
        # re-check against the raw input data rather than self.bot_mode.
        mode = info.data.get("bot_mode", "webhook")
        if mode == "webhook" and not v:
            raise ValueError(
                "WEBHOOK_HOST must be set in .env when BOT_MODE=webhook "
                "(e.g. WEBHOOK_HOST=https://bot.yourdomain.com)"
            )
        return v

    # PostgreSQL Database — no default. Must come from .env (DATABASE_URL=...).
    database_url: str
    db_echo: bool = Field(default=False)
    db_pool_size: int = Field(default=20)
    db_max_overflow: int = Field(default=10)

    # Redis — no default. Must come from .env (REDIS_URL=...).
    redis_url: str
    redis_ttl_queue_key: str = Field(default="rgcbot:ttl:queue")
    redis_rate_limit_prefix: str = Field(default="rgcbot:ratelimit:")

    # Auto-Delete TTL Defaults (seconds) — safe to keep as defaults, these
    # are tunable behavior, not environment-specific secrets/endpoints.
    default_mod_ttl: int = Field(default=15)
    default_fun_ttl: int = Field(default=30)
    default_rules_ttl: int = Field(default=45)
    default_warn_ttl: int = Field(default=20)
    default_general_ttl: int = Field(default=30)
    sweeper_interval_seconds: float = Field(default=1.5)
    sweeper_batch_size: int = Field(default=100)

    # Moderation & Anti-Spam Defaults
    default_flood_limit: int = Field(default=5)
    default_flood_window: int = Field(default=3)
    default_captcha_timeout: int = Field(default=90)
    default_log_channel_id: Optional[int] = Field(default=None)

    # Logging
    log_level: str = Field(default="INFO")

    @property
    def webhook_url(self) -> str:
        return f"{self.webhook_host.rstrip('/')}{self.webhook_path}"


settings = Settings()