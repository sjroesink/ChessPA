import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, func, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class Game(Base):
    __tablename__ = "games"
    __table_args__ = (
        Index("ix_games_user_played", "user_id", "played_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    platform: Mapped[str] = mapped_column(String(20))
    platform_game_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pgn: Mapped[str] = mapped_column(Text)
    white_username: Mapped[str] = mapped_column(String(100))
    black_username: Mapped[str] = mapped_column(String(100))
    user_color: Mapped[str] = mapped_column(String(5))
    result: Mapped[str] = mapped_column(String(4))
    opening_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    opening_eco: Mapped[str | None] = mapped_column(String(10), nullable=True)
    time_control: Mapped[str | None] = mapped_column(String(20), nullable=True)
    user_elo: Mapped[int | None] = mapped_column(Integer, nullable=True)
    opponent_elo: Mapped[int | None] = mapped_column(Integer, nullable=True)
    played_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    move_count: Mapped[int] = mapped_column(Integer, default=0)
    import_source: Mapped[str] = mapped_column(String(20))
    content_hash: Mapped[str] = mapped_column(String(64), unique=True)
    analysis_status: Mapped[str] = mapped_column(String(20), default="pending")
    # Game-level progressive stage indicator for quick UI surfacing (games list chip).
    # Values: "none" | "shallow" | "standard" | "deep"
    analysis_stage: Mapped[str | None] = mapped_column(String(10), nullable=True)

    def __init__(self, **kwargs):
        if "analysis_status" not in kwargs:
            kwargs["analysis_status"] = "pending"
        if "move_count" not in kwargs:
            kwargs["move_count"] = 0
        super().__init__(**kwargs)

    user = relationship("User", back_populates="games")
    move_analyses = relationship("MoveAnalysis", back_populates="game", cascade="all, delete-orphan")
    summary = relationship("GameSummary", back_populates="game", uselist=False, cascade="all, delete-orphan")
