from datetime import datetime
from sqlalchemy import BigInteger, DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from src.core.database import Base


class ApprovedUser(Base):
    __tablename__ = "approved_users"
    __table_args__ = (UniqueConstraint("chat_id", "user_id", name="uq_approved_chat_user"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    approved_by: Mapped[int] = mapped_column(BigInteger)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
