from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.core.database import Base


class TTLSettings(Base):
    __tablename__ = "ttl_settings"

    chat_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("groups.chat_id", ondelete="CASCADE"), primary_key=True
    )

    # TTL in seconds per category (0 means auto-delete is disabled for that category)
    mod_ttl: Mapped[int] = mapped_column(Integer, default=15)
    fun_ttl: Mapped[int] = mapped_column(Integer, default=30)
    rules_ttl: Mapped[int] = mapped_column(Integer, default=45)
    warn_ttl: Mapped[int] = mapped_column(Integer, default=20)
    general_ttl: Mapped[int] = mapped_column(Integer, default=30)

    # Whether the user command trigger (e.g. /ban, /dice) should also be auto-deleted
    delete_command_trigger: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    group = relationship("Group", back_populates="ttl_settings")
