from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.core.database import Base


class BlocklistTerm(Base):
    __tablename__ = "blocklist_terms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("groups.chat_id", ondelete="CASCADE"), index=True
    )
    term: Mapped[str] = mapped_column(String(255), index=True)
    action: Mapped[str] = mapped_column(String(32), default="delete")  # delete, warn, mute, ban
    warn_count: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    group = relationship("Group", back_populates="blocklist_terms")
