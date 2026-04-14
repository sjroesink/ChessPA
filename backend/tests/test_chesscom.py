from unittest.mock import AsyncMock, MagicMock, patch

from app.chess_services.chesscom import fetch_games_for_month, fetch_all_game_months


SAMPLE_ARCHIVES_RESPONSE = {
    "archives": [
        "https://api.chess.com/pub/player/testuser/games/2026/03",
        "https://api.chess.com/pub/player/testuser/games/2026/04",
    ]
}

SAMPLE_GAMES_RESPONSE = {
    "games": [
        {
            "url": "https://www.chess.com/game/live/12345",
            "pgn": '[Event "Live Chess"]\n[White "testuser"]\n[Black "opponent"]\n[Result "1-0"]\n[TimeControl "600"]\n\n1. e4 e5 1-0',
            "time_control": "600",
            "rated": True,
            "white": {"username": "testuser", "rating": 1700},
            "black": {"username": "opponent", "rating": 1650},
        }
    ]
}


async def test_fetch_all_game_months():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = SAMPLE_ARCHIVES_RESPONSE
    mock_response.raise_for_status = MagicMock()

    with patch("app.chess_services.chesscom.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_cls.return_value = mock_client

        months = await fetch_all_game_months("testuser")

    assert len(months) == 2
    assert "2026/03" in months[0]


async def test_fetch_games_for_month():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = SAMPLE_GAMES_RESPONSE
    mock_response.raise_for_status = MagicMock()

    with patch("app.chess_services.chesscom.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_cls.return_value = mock_client

        games = await fetch_games_for_month("https://api.chess.com/pub/player/testuser/games/2026/04")

    assert len(games) == 1
    assert games[0]["pgn"] is not None
    assert games[0]["white"]["username"] == "testuser"
