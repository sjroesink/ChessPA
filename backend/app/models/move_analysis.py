import uuid

from sqlalchemy import Boolean, String, Integer, Float, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
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

    # Rich analysis additions (all nullable — pre-existing rows stay valid)
    win_percent_before: Mapped[float | None] = mapped_column(Float, nullable=True)
    win_percent_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    accuracy_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_critical_moment: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    maia_top1_san: Mapped[str | None] = mapped_column(String(10), nullable=True)
    maia_top1_prob: Mapped[float | None] = mapped_column(Float, nullable=True)
    maia_match_played: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    maia_rating_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # details_json shape:
    # {
    #   "multipv": [{"rank": 1, "san": "Nf3", "uci": "g1f3", "eval_cp": 25, "pv_san": ["Nf3","Nc6","Bb5"]}, ...],
    #   "motifs": [{"type": "fork", "attacker": "d4", "squares": ["e6","c6"], "verified_gain_cp": 200}],
    #   "features": {"phase": "middlegame", "pawn_structure": {...}, "king_safety": {...}}
    # }
    details_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    game = relationship("Game", back_populates="move_analyses")
