from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class UserProfileChange(Base):
    __tablename__ = "user_profile_changes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), index=True
    )
    chat_id: Mapped[int | None] = mapped_column(BigInteger, index=True, nullable=True)
    old_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    new_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    old_first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    new_first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)