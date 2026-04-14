import httpx

CHESS_COM_API = "https://api.chess.com/pub"
USER_AGENT = "ChessPA/0.1"


async def fetch_all_game_months(username: str) -> list[str]:
    """Fetch list of archive URLs (one per month) for a Chess.com user."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{CHESS_COM_API}/player/{username.lower()}/games/archives",
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        return response.json()["archives"]


async def fetch_games_for_month(archive_url: str) -> list[dict]:
    """Fetch all games from a specific month archive URL."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            archive_url,
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
        return response.json().get("games", [])


async def fetch_recent_games(username: str, since_timestamp: int | None = None) -> list[dict]:
    """Fetch games from the most recent month(s). Optionally filter by timestamp."""
    archives = await fetch_all_game_months(username)
    if not archives:
        return []

    all_games = []
    for archive_url in archives[-2:]:
        games = await fetch_games_for_month(archive_url)
        all_games.extend(games)

    if since_timestamp:
        all_games = [g for g in all_games if g.get("end_time", 0) > since_timestamp]

    return all_games
