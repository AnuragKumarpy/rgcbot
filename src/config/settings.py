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

    # Bot API Token
    bot_token: str = Field(default="1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ")

    # Mode: polling or webhook
    bot_mode: Literal["polling", "webhook"] = Field(default="polling")

    # Webhook server configuration
    webhook_host: str = Field(default="https://yourdomain.com")
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


    # PostgreSQL Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/rgcbot"
    )
    db_echo: bool = Field(default=False)
    db_pool_size: int = Field(default=20)
    db_max_overflow: int = Field(default=10)

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0")
    redis_ttl_queue_key: str = Field(default="rgcbot:ttl:queue")
    redis_rate_limit_prefix: str = Field(default="rgcbot:ratelimit:")

    # Auto-Delete TTL Defaults (seconds)
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
