import uuid

from sqlalchemy import String, Integer, Float, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class MoveAnalysis(Base):
    __tablename__ = "move_analyses"
    __table_args__ = (
        Index("ix_move_analyses_game", "game_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("games.id"))
    move_number: Mapped[int] = mapped_column(Integer)
    color: Mapped[str] = mapped_column(String(5))
    move_san: Mapped[str] = mapped_column(String(10))
    eval_before: Mapped[float] = mapped_column(Float)
    eval_after: Mapped[float] = mapped_column(Float)
    best_move_san: Mapped[str] = mapped_column(String(10))
    classification: Mapped[str] = mapped_column(String(15))
    fen: Mapped[str | None] = mapped_column(String(100), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    time_spent_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)

    game = relationship("Game", back_populates="move_analyses")
