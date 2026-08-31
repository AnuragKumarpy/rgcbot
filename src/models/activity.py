from datetime import date
from sqlalchemy import BigInteger, Date, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from src.core.database import Base


class UserActivity(Base):
    __tablename__ = "user_activity"
    __table_args__ = (
        UniqueConstraint("chat_id", "user_id", "date", name="uq_user_chat_activity_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    date: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    messages_count: Mapped[int] = mapped_column(Integer, default=0)
    stickers_count: Mapped[int] = mapped_column(Integer, default=0)
    media_count: Mapped[int] = mapped_column(Integer, default=0)
    voice_count: Mapped[int] = mapped_column(Integer, default=0)
