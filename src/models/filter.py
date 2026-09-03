from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.core.database import Base


class GroupFilter(Base):
    __tablename__ = "group_filters"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("groups.chat_id", ondelete="CASCADE"), index=True
    )

    keyword: Mapped[str] = mapped_column(String(128), index=True)
    response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    media_type: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )  # photo, video, sticker, document, voice
    is_exact_match: Mapped[bool] = mapped_column(Boolean, default=False)
    custom_ttl: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )  # Override TTL in seconds

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    group = relationship("Group", back_populates="filters")
