from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.core.database import Base


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str] = mapped_column(String(255), default="")
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Gamification & Economy
    karma: Mapped[int] = mapped_column(Integer, default=0, index=True)
    coins: Mapped[int] = mapped_column(Integer, default=100)
    daily_streak: Mapped[int] = mapped_column(Integer, default=0)
    last_daily_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Customization & Flairs
    custom_title: Mapped[str | None] = mapped_column(String(64), nullable=True)
    badges: Mapped[str] = mapped_column(String(255), default="⭐ Member")

    # AFK Status
    is_afk: Mapped[bool] = mapped_column(Boolean, default=False)
    afk_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    afk_since: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    group_memberships = relationship("GroupMember", back_populates="user", cascade="all, delete-orphan")
