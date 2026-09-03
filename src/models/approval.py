# src/models/approval.py
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from src.core.database import Base


class ChatApproval(Base):
    __tablename__ = "chat_approvals"
    __table_args__ = (
        UniqueConstraint("chat_id", "user_id", "approval_type", name="uq_chat_user_approval"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    approval_type: Mapped[str] = mapped_column(String(64), default="link_media_filter", index=True)
    granted_by: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
