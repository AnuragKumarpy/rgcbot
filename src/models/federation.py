import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


def generate_fed_id() -> str:
    return uuid.uuid4().hex[:12]


class Federation(Base):
    __tablename__ = "federations"

    fed_id: Mapped[str] = mapped_column(String(32), primary_key=True, default=generate_fed_id)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    owner_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    admins = relationship("FederationAdmin", back_populates="federation", cascade="all, delete-orphan")
    groups = relationship("FederationGroup", back_populates="federation", cascade="all, delete-orphan")
    bans = relationship("FederationBan", back_populates="federation", cascade="all, delete-orphan")


class FederationAdmin(Base):
    __tablename__ = "federation_admins"
    __table_args__ = (UniqueConstraint("fed_id", "user_id", name="uq_fed_admin"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fed_id: Mapped[str] = mapped_column(String(32), ForeignKey("federations.fed_id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    promoted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    federation = relationship("Federation", back_populates="admins")


class FederationGroup(Base):
    __tablename__ = "federation_groups"
    __table_args__ = (UniqueConstraint("chat_id", name="uq_fed_group_chat"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fed_id: Mapped[str] = mapped_column(String(32), ForeignKey("federations.fed_id", ondelete="CASCADE"), index=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("groups.chat_id", ondelete="CASCADE"), index=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    federation = relationship("Federation", back_populates="groups")


class FederationBan(Base):
    __tablename__ = "federation_bans"
    __table_args__ = (UniqueConstraint("fed_id", "user_id", name="uq_fed_ban_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fed_id: Mapped[str] = mapped_column(String(32), ForeignKey("federations.fed_id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    banned_by_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    banned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    federation = relationship("Federation", back_populates="bans")
