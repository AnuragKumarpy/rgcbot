from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.core.database import Base


class ModerationLog(Base):
    __tablename__ = "moderation_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("groups.chat_id", ondelete="CASCADE"), index=True)
    target_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), index=True)
    admin_user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)

    action_type: Mapped[str] = mapped_column(String(32), index=True)  # ban, mute, kick, warn, antispam_trigger
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    group = relationship("Group", back_populates="moderation_logs")
    target_user = relationship("User", foreign_keys=[target_user_id])
    admin_user = relationship("User", foreign_keys=[admin_user_id])
