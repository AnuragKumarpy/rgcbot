from datetime import datetime
from typing import Optional
from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from src.core.database import Base


class BroadcastRecord(Base):
    __tablename__ = "broadcast_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_id: Mapped[int] = mapped_column(BigInteger, index=True)
    target_type: Mapped[str] = mapped_column(String(32))  # users, groups, all
    content: Mapped[str] = mapped_column(Text)
    media_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    media_file_id: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    total_targets: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="completed")  # queued, sending, completed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
