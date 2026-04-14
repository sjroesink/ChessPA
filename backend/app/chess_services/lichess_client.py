import json

import httpx

LICHESS_API = "https://lichess.org/api"


async def fetch_recent_games(
    username: str,
    max_games: int = 100,
    since: int | None = None,
    token: str | None = None,
) -> list[dict]:
    """Fetch recent games from Lichess as NDJSON."""
    params: dict = {
        "max": max_games,
        "pgnInJson": "true",
    }
    if since:
        params["since"] = since

    headers = {"Accept": "application/x-ndjson"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{LICHESS_API}/games/user/{username}",
            params=params,
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()

        games = []
        for line in response.text.strip().split("\n"):
            if line.strip():
                games.append(json.loads(line))
        return games
