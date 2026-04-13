from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.models.user import User
from app.models.connected_account import ConnectedAccount
from app.models.game import Game
from app.models.move_analysis import MoveAnalysis
from app.models.game_summary import GameSummary
from app.models.coaching_insight import CoachingInsight

__all__ = [
    "Base",
    "User",
    "ConnectedAccount",
    "Game",
    "MoveAnalysis",
    "GameSummary",
    "CoachingInsight",
]
