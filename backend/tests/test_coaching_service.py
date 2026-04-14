import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

from app.models.game import Game
from app.models.game_summary import GameSummary
from app.models.coaching_insight import CoachingInsight
from app.coaching.service import generate_coaching_insights


MOCK_LLM_RESPONSE = '''{
  "insights": [
    {
      "type": "weakness",
      "title": "Blunders in het middenspel",
      "description": "Je maakt veel fouten in het middenspel. Focus op tactische patronen.",
      "severity": "high",
      "related_game_indices": [0, 1]
    },
    {
      "type": "strength",
      "title": "Sterke opening",
      "description": "Je openingsspel is consistent sterk. Blijf dit zo doen.",
      "severity": "low",
      "related_game_indices": [0]
    },
    {
      "type": "pattern",
      "title": "Tijdnood na zet 25",
      "description": "Je besteedt te veel tijd in de opening waardoor je in tijdnood komt.",
      "severity": "medium",
      "related_game_indices": [1, 2]
    }
  ]
}'''


def _make_game(i: int, user_id: uuid.UUID) -> Game:
    """Create a Game object with test data."""
    game = Game(
        user_id=user_id,
        platform="chess_com",
        pgn=f"1. e4 e5 {i} 1-0",
        white_username="coach_test",
        black_username=f"opponent{i}",
        user_color="white",
        result="win" if i % 2 == 0 else "loss",
        opening_name="Sicilian Defense",
        time_control="600",
        user_elo=1700,
        opponent_elo=1650,
        played_at=datetime(2026, 4, 10, tzinfo=timezone.utc),
        move_count=30,
        import_source="sync",
        content_hash=f"coaching-test-{i}",
        analysis_status="done",
    )
    game.id = uuid.uuid4()
    return game


def _make_summary(game_id: uuid.UUID, i: int) -> GameSummary:
    """Create a GameSummary object with test data."""
    summary = GameSummary(
        game_id=game_id,
        blunders=i,
        mistakes=i + 1,
        inaccuracies=i + 2,
        avg_eval_loss=10.0 + i * 5,
        phase_scores={"opening": 90, "middlegame": 70, "endgame": 60},
        time_trouble=False,
    )
    return summary


def _mock_db_session(games, summaries):
    """Create a mock AsyncSession that returns the given games and summaries."""
    db = AsyncMock()

    # First execute call: games query
    games_result = MagicMock()
    games_scalars = MagicMock()
    games_scalars.all.return_value = games
    games_result.scalars.return_value = games_scalars

    # Second execute call: summaries query
    summaries_result = MagicMock()
    summaries_scalars = MagicMock()
    summaries_scalars.all.return_value = summaries
    summaries_result.scalars.return_value = summaries_scalars

    # Third execute call: delete old insights
    delete_result = MagicMock()

    db.execute = AsyncMock(
        side_effect=[games_result, summaries_result, delete_result]
    )
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    return db


async def test_generate_coaching_insights():
    user_id = uuid.uuid4()

    # Create test games and summaries
    games = [_make_game(i, user_id) for i in range(5)]
    summaries = [_make_summary(g.id, i) for i, g in enumerate(games)]

    db = _mock_db_session(games, summaries)

    mock_provider = AsyncMock()
    mock_provider.generate = AsyncMock(return_value=MOCK_LLM_RESPONSE)

    with patch("app.coaching.service.get_llm_provider", return_value=mock_provider):
        insights = await generate_coaching_insights(db, user_id)

    assert len(insights) == 3
    assert insights[0].type == "weakness"
    assert insights[0].title == "Blunders in het middenspel"
    assert insights[1].type == "strength"
    assert insights[2].type == "pattern"
    assert insights[0].user_id == user_id
    assert len(insights[0].related_games) == 2

    # Verify LLM was called with correct prompts
    mock_provider.generate.assert_called_once()
    call_args = mock_provider.generate.call_args
    assert "1700" in call_args[0][1]  # elo in user prompt
    assert "Sicilian Defense" in call_args[0][1]  # opening in user prompt

    # Verify DB interactions
    assert db.add.call_count == 3  # 3 insights added
    db.commit.assert_called_once()
    assert db.refresh.call_count == 3


async def test_generate_coaching_not_enough_games():
    user_id = uuid.uuid4()

    # Only 2 games — below minimum of 3
    games = [_make_game(i, user_id) for i in range(2)]

    db = AsyncMock()
    games_result = MagicMock()
    games_scalars = MagicMock()
    games_scalars.all.return_value = games
    games_result.scalars.return_value = games_scalars
    db.execute = AsyncMock(return_value=games_result)

    insights = await generate_coaching_insights(db, user_id)
    assert insights == []


async def test_generate_coaching_no_games():
    user_id = uuid.uuid4()

    db = AsyncMock()
    games_result = MagicMock()
    games_scalars = MagicMock()
    games_scalars.all.return_value = []
    games_result.scalars.return_value = games_scalars
    db.execute = AsyncMock(return_value=games_result)

    insights = await generate_coaching_insights(db, user_id)
    assert insights == []


async def test_generate_coaching_invalid_llm_response():
    user_id = uuid.uuid4()
    games = [_make_game(i, user_id) for i in range(5)]
    summaries = [_make_summary(g.id, i) for i, g in enumerate(games)]

    db = _mock_db_session(games, summaries)

    mock_provider = AsyncMock()
    mock_provider.generate = AsyncMock(return_value="This is not valid JSON at all")

    with patch("app.coaching.service.get_llm_provider", return_value=mock_provider):
        insights = await generate_coaching_insights(db, user_id)

    assert insights == []


async def test_generate_coaching_markdown_wrapped_response():
    """LLM sometimes wraps JSON in markdown code fences."""
    user_id = uuid.uuid4()
    games = [_make_game(i, user_id) for i in range(5)]
    summaries = [_make_summary(g.id, i) for i, g in enumerate(games)]

    db = _mock_db_session(games, summaries)

    wrapped_response = f"```json\n{MOCK_LLM_RESPONSE}\n```"
    mock_provider = AsyncMock()
    mock_provider.generate = AsyncMock(return_value=wrapped_response)

    with patch("app.coaching.service.get_llm_provider", return_value=mock_provider):
        insights = await generate_coaching_insights(db, user_id)

    assert len(insights) == 3
    assert insights[0].type == "weakness"


async def test_generate_coaching_limits_to_five_insights():
    """Even if LLM returns more than 5 insights, only persist 5."""
    user_id = uuid.uuid4()
    games = [_make_game(i, user_id) for i in range(5)]
    summaries = [_make_summary(g.id, i) for i, g in enumerate(games)]

    db = _mock_db_session(games, summaries)

    many_insights = {
        "insights": [
            {
                "type": "weakness",
                "title": f"Insight {i}",
                "description": f"Description {i}",
                "severity": "medium",
                "related_game_indices": [0],
            }
            for i in range(8)
        ]
    }
    import json

    mock_provider = AsyncMock()
    mock_provider.generate = AsyncMock(return_value=json.dumps(many_insights))

    with patch("app.coaching.service.get_llm_provider", return_value=mock_provider):
        insights = await generate_coaching_insights(db, user_id)

    assert len(insights) == 5


async def test_generate_coaching_maps_game_indices():
    """related_game_indices should map to actual game UUIDs."""
    user_id = uuid.uuid4()
    games = [_make_game(i, user_id) for i in range(5)]
    summaries = [_make_summary(g.id, i) for i, g in enumerate(games)]

    db = _mock_db_session(games, summaries)

    single_insight_response = '''{
      "insights": [
        {
          "type": "weakness",
          "title": "Test",
          "description": "Test desc",
          "severity": "high",
          "related_game_indices": [0, 2, 4]
        }
      ]
    }'''

    mock_provider = AsyncMock()
    mock_provider.generate = AsyncMock(return_value=single_insight_response)

    with patch("app.coaching.service.get_llm_provider", return_value=mock_provider):
        insights = await generate_coaching_insights(db, user_id)

    assert len(insights) == 1
    assert insights[0].related_games == [games[0].id, games[2].id, games[4].id]


async def test_generate_coaching_ignores_out_of_range_indices():
    """Out-of-range game indices should be silently skipped."""
    user_id = uuid.uuid4()
    games = [_make_game(i, user_id) for i in range(5)]
    summaries = [_make_summary(g.id, i) for i, g in enumerate(games)]

    db = _mock_db_session(games, summaries)

    response_with_bad_indices = '''{
      "insights": [
        {
          "type": "weakness",
          "title": "Test",
          "description": "Test desc",
          "severity": "high",
          "related_game_indices": [0, 99, -1, 2]
        }
      ]
    }'''

    mock_provider = AsyncMock()
    mock_provider.generate = AsyncMock(return_value=response_with_bad_indices)

    with patch("app.coaching.service.get_llm_provider", return_value=mock_provider):
        insights = await generate_coaching_insights(db, user_id)

    assert len(insights) == 1
    # Only index 0 and 2 are valid (index -1 fails 0 <= idx check)
    assert len(insights[0].related_games) == 2
    assert insights[0].related_games == [games[0].id, games[2].id]
