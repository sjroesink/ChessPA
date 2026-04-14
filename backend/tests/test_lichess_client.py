from unittest.mock import AsyncMock, MagicMock, patch

from app.chess_services.lichess_client import fetch_recent_games


SAMPLE_NDJSON = (
    '{"id":"abc123","rated":true,"variant":"standard","speed":"rapid",'
    '"perf":"rapid","createdAt":1712700000000,"lastMoveAt":1712703600000,'
    '"status":"mate","players":{"white":{"user":{"name":"testuser","id":"testuser"},"rating":1700},'
    '"black":{"user":{"name":"opponent","id":"opponent"},"rating":1650}},'
    '"winner":"white","moves":"e4 e5 Nf3 Nc6","opening":{"eco":"C44","name":"Kings Pawn Game"},'
    '"clock":{"initial":600,"increment":0,"totalTime":600},"pgn":"1. e4 e5 1-0"}\n'
)


async def test_fetch_recent_games():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = SAMPLE_NDJSON
    mock_response.raise_for_status = MagicMock()

    with patch("app.chess_services.lichess_client.httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_cls.return_value = mock_client

        games = await fetch_recent_games("testuser")

    assert len(games) == 1
    assert games[0]["players"]["white"]["user"]["name"] == "testuser"
    assert games[0]["winner"] == "white"
