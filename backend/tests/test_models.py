import uuid

from app.models import User, ConnectedAccount, Game, MoveAnalysis, GameSummary, CoachingInsight


def test_user_creation():
    user = User(username="testplayer")
    assert user.username == "testplayer"
    assert user.preferences == {}


def test_connected_account_creation():
    user_id = uuid.uuid4()
    account = ConnectedAccount(
        user_id=user_id,
        platform="lichess",
        platform_username="testplayer",
        auto_sync=True,
    )
    assert account.platform == "lichess"
    assert account.auto_sync is True


def test_game_creation():
    from datetime import datetime, timezone

    game = Game(
        user_id=uuid.uuid4(),
        platform="chess_com",
        pgn="1. e4 e5 *",
        white_username="player1",
        black_username="player2",
        user_color="white",
        result="win",
        played_at=datetime.now(timezone.utc),
        import_source="sync",
        content_hash="abc123",
    )
    assert game.analysis_status == "pending"
    assert game.result == "win"


def test_move_analysis_creation():
    analysis = MoveAnalysis(
        game_id=uuid.uuid4(),
        move_number=14,
        color="white",
        move_san="Bxf7+",
        eval_before=0.5,
        eval_after=-2.7,
        best_move_san="O-O",
        classification="blunder",
    )
    assert analysis.classification == "blunder"
    assert analysis.eval_after == -2.7


def test_game_summary_creation():
    summary = GameSummary(
        game_id=uuid.uuid4(),
        blunders=2,
        mistakes=3,
        inaccuracies=5,
        avg_eval_loss=0.45,
        phase_scores={"opening": 92, "middle": 71, "endgame": 65},
        time_trouble=True,
    )
    assert summary.blunders == 2
    assert summary.phase_scores["middle"] == 71


def test_coaching_insight_creation():
    insight = CoachingInsight(
        user_id=uuid.uuid4(),
        type="weakness",
        title="Queen endgame struggles",
        description="You lose material in queen endgames frequently.",
        severity="high",
        related_games=[uuid.uuid4(), uuid.uuid4()],
        model_version="claude-sonnet-4-6",
    )
    assert insight.type == "weakness"
    assert len(insight.related_games) == 2
