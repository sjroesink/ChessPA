import uuid
from datetime import datetime

from sqlalchemy import Integer, Float, Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class GameSummary(Base):
    __tablename__ = "game_summaries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("games.id"), unique=True)
    blunders: Mapped[int] = mapped_column(Integer, default=0)
    mistakes: Mapped[int] = mapped_column(Integer, default=0)
    inaccuracies: Mapped[int] = mapped_column(Integer, default=0)
    avg_eval_loss: Mapped[float] = mapped_column(Float, default=0.0)
    phase_scores: Mapped[dict] = mapped_column(JSONB, default=dict)
    time_trouble: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Rich analysis additions (nullable — pre-existing rows stay valid)
    accuracy_white: Mapped[float | None] = mapped_column(Float, nullable=True)
    accuracy_black: Mapped[float | None] = mapped_column(Float, nullable=True)
    opening_eco: Mapped[str | None] = mapped_column(String(5), nullable=True)
    opening_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    phase_acpl: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # {opening, middlegame, endgame: cpl}
    motif_counts: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # {fork: n, pin: n, ...}

    game = relationship("Game", back_populates="summary")
