from datetime import datetime
from typing import Optional
from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.core.database import Base


class Group(Base):
    __tablename__ = "groups"

    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), default="Unknown Group")
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Welcome & Verification Gate
    welcome_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    welcome_text: Mapped[str] = mapped_column(
        Text,
        default="✨ Welcome {mention} to <b>{chat_title}</b> 💎\nPlease review the group rules and enjoy your stay!",
    )
    welcome_media_type: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True
    )  # photo, video, animation
    welcome_media_file_id: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    welcome_buttons: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Button text | url

    captcha_mode: Mapped[str] = mapped_column(String(32), default="button")  # button, math, off
    captcha_timeout_sec: Mapped[int] = mapped_column(Integer, default=90)

    # Moderation & Anti-Spam
    antispam_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    antiflood_limit: Mapped[int] = mapped_column(Integer, default=5)
    antiflood_window_sec: Mapped[int] = mapped_column(Integer, default=3)
    antiforward_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    antilink_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    english_only_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    tos_shield_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Warn settings
    max_warns: Mapped[int] = mapped_column(Integer, default=3)
    warn_action: Mapped[str] = mapped_column(String(32), default="mute")  # mute, kick, ban
    warn_duration_sec: Mapped[int] = mapped_column(Integer, default=3600)  # 1 hour default

    # Locks, CleanService & Anti-Channel
    locked_types: Mapped[Optional[str]] = mapped_column(
        Text, default=""
    )  # comma-separated locked types
    clean_service_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    antichannel_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    antichannel_mode: Mapped[str] = mapped_column(String(16), default="del")  # del, ban

    # Night Mode / Slowmode
    night_mode_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    night_mode_start: Mapped[str] = mapped_column(String(5), default="00:00")
    night_mode_end: Mapped[str] = mapped_column(String(5), default="06:00")

    # Logging Channel
    log_channel_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # Rules
    rules_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rules_button_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")
    moderation_logs = relationship(
        "ModerationLog", back_populates="group", cascade="all, delete-orphan"
    )
    filters = relationship("GroupFilter", back_populates="group", cascade="all, delete-orphan")
    blocklist_terms = relationship(
        "BlocklistTerm", back_populates="group", cascade="all, delete-orphan"
    )
    ttl_settings = relationship(
        "TTLSettings", back_populates="group", uselist=False, cascade="all, delete-orphan"
    )
