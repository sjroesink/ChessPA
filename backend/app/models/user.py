import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    preferences: Mapped[dict] = mapped_column(JSONB, default=dict)

    def __init__(self, **kwargs):
        if "preferences" not in kwargs:
            kwargs["preferences"] = {}
        super().__init__(**kwargs)

    connected_accounts = relationship("ConnectedAccount", back_populates="user")
    games = relationship("Game", back_populates="user")
    coaching_insights = relationship("CoachingInsight", back_populates="user")
