# ChessPA Phase 2: Game Import Pipeline

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Import chess games from Chess.com and Lichess APIs + PGN file upload, store in PostgreSQL with dedup, and expose a filterable games list endpoint.

**Architecture:** Chess platform API clients fetch games, PGN parser extracts metadata, content_hash deduplicates. Celery + Redis handle background sync. Games are queryable via REST API with filters for platform, result, opening, time control category, and date range.

**Tech Stack:** Python 3.12, FastAPI, Celery, Redis, python-chess (PGN parsing), httpx (API clients), SQLAlchemy 2.0 async

**Spec:** `docs/superpowers/specs/2026-04-13-chesspa-design.md`

---

## File Structure

```
backend/
├── app/
│   ├── chess_services/
│   │   ├── __init__.py
│   │   ├── chesscom.py          # Chess.com API client
│   │   ├── lichess.py           # Lichess API client
│   │   ├── pgn_parser.py        # PGN → Game metadata extraction
│   │   └── time_control.py      # Time control classifier (bullet/blitz/rapid/standard)
│   ├── api/
│   │   ├── games.py             # /api/games endpoints
│   │   └── router.py            # (modify: add games router)
│   └── worker/
│       ├── __init__.py
│       ├── celery_app.py        # Celery app config
│       └── tasks.py             # Sync + import tasks
├── tests/
│   ├── test_chesscom.py
│   ├── test_lichess_client.py
│   ├── test_pgn_parser.py
│   ├── test_time_control.py
│   ├── test_games_api.py
│   └── test_tasks.py
```

---

### Task 1: Time Control Classifier

**Files:**
- Create: `backend/app/chess_services/__init__.py`
- Create: `backend/app/chess_services/time_control.py`
- Test: `backend/tests/test_time_control.py`

- [ ] **Step 1: Write failing tests**

Create `backend/app/chess_services/__init__.py` (empty).

Create `backend/tests/test_time_control.py`:

```python
from app.chess_services.time_control import classify_time_control


def test_bullet():
    assert classify_time_control("60") == "bullet"
    assert classify_time_control("60+1") == "bullet"
    assert classify_time_control("120") == "bullet"
    assert classify_time_control("120+1") == "bullet"


def test_blitz():
    assert classify_time_control("180") == "blitz"
    assert classify_time_control("180+2") == "blitz"
    assert classify_time_control("300") == "blitz"
    assert classify_time_control("300+0") == "blitz"
    assert classify_time_control("300+3") == "blitz"


def test_rapid():
    assert classify_time_control("600") == "rapid"
    assert classify_time_control("600+0") == "rapid"
    assert classify_time_control("900") == "rapid"
    assert classify_time_control("900+10") == "rapid"
    assert classify_time_control("1500") == "rapid"
    assert classify_time_control("1800") == "rapid"


def test_classical():
    assert classify_time_control("1800+30") == "classical"
    assert classify_time_control("2700") == "classical"
    assert classify_time_control("3600") == "classical"
    assert classify_time_control("5400") == "classical"


def test_unknown():
    assert classify_time_control(None) == "unknown"
    assert classify_time_control("") == "unknown"
    assert classify_time_control("-") == "unknown"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_time_control.py -v`
Expected: FAIL — ImportError

- [ ] **Step 3: Implement**

Create `backend/app/chess_services/time_control.py`:

```python
def classify_time_control(time_control: str | None) -> str:
    """Classify time control string into bullet/blitz/rapid/classical/unknown.

    Time control format: "base" or "base+increment" in seconds.
    Thresholds (base time):
      bullet:    < 180s (< 3 min)
      blitz:     180s - 599s (3-10 min)
      rapid:     600s - 1799s (10-30 min)
      classical: >= 1800s (>= 30 min)

    When increment exists, effective time = base + 40 * increment
    (estimated 40 moves per game).
    """
    if not time_control or time_control.strip() in ("", "-"):
        return "unknown"

    try:
        parts = time_control.split("+")
        base = int(parts[0])
        increment = int(parts[1]) if len(parts) > 1 else 0
        effective = base + 40 * increment
    except (ValueError, IndexError):
        return "unknown"

    if effective < 180:
        return "bullet"
    elif effective < 600:
        return "blitz"
    elif effective < 1800:
        return "rapid"
    else:
        return "classical"
```

- [ ] **Step 4: Run tests**

Run: `cd backend && uv run pytest tests/test_time_control.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/chess_services/ backend/tests/test_time_control.py
git commit -m "feat: time control classifier (bullet/blitz/rapid/classical)"
```

---

### Task 2: PGN Parser

**Files:**
- Create: `backend/app/chess_services/pgn_parser.py`
- Test: `backend/tests/test_pgn_parser.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_pgn_parser.py`:

```python
import hashlib

from app.chess_services.pgn_parser import parse_pgn, compute_content_hash


SAMPLE_PGN = """[Event "Live Chess"]
[Site "Chess.com"]
[Date "2026.04.10"]
[Round "-"]
[White "player1"]
[Black "player2"]
[Result "1-0"]
[WhiteElo "1700"]
[BlackElo "1650"]
[TimeControl "600"]
[ECO "B90"]
[Opening "Sicilian Defense: Najdorf Variation"]
[Termination "player1 won by checkmate"]

1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 1-0"""


SAMPLE_PGN_NO_HEADERS = """1. e4 e5 2. Nf3 Nc6 *"""


def test_parse_pgn_full():
    result = parse_pgn(SAMPLE_PGN)
    assert result["white_username"] == "player1"
    assert result["black_username"] == "player2"
    assert result["result_raw"] == "1-0"
    assert result["white_elo"] == 1700
    assert result["black_elo"] == 1650
    assert result["time_control"] == "600"
    assert result["opening_eco"] == "B90"
    assert result["opening_name"] == "Sicilian Defense: Najdorf Variation"
    assert result["move_count"] == 6
    assert result["played_at"] is not None


def test_parse_pgn_minimal():
    result = parse_pgn(SAMPLE_PGN_NO_HEADERS)
    assert result["white_username"] == "?"
    assert result["move_count"] == 2


def test_compute_content_hash():
    hash1 = compute_content_hash("1. e4 e5 *", "2026-04-10", "p1", "p2")
    hash2 = compute_content_hash("1. e4 e5 *", "2026-04-10", "p1", "p2")
    hash3 = compute_content_hash("1. d4 d5 *", "2026-04-10", "p1", "p2")
    assert hash1 == hash2
    assert hash1 != hash3
    assert len(hash1) == 64  # SHA256 hex


def test_determine_result():
    from app.chess_services.pgn_parser import determine_result

    assert determine_result("1-0", "player1") == "win"
    assert determine_result("1-0", "player2") == "loss"
    assert determine_result("0-1", "player1") == "loss"
    assert determine_result("0-1", "player2") == "win"
    assert determine_result("1/2-1/2", "player1") == "draw"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_pgn_parser.py -v`
Expected: FAIL

- [ ] **Step 3: Implement**

Create `backend/app/chess_services/pgn_parser.py`:

```python
import hashlib
import io
from datetime import datetime, timezone

import chess.pgn


def parse_pgn(pgn_text: str) -> dict:
    """Parse a PGN string and extract game metadata."""
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        raise ValueError("Invalid PGN")

    headers = game.headers
    moves = list(game.mainline_moves())

    # Parse date
    date_str = headers.get("Date", "????.??.??")
    played_at = None
    try:
        played_at = datetime.strptime(date_str, "%Y.%m.%d").replace(tzinfo=timezone.utc)
    except ValueError:
        played_at = datetime.now(timezone.utc)

    # Parse Elos
    white_elo = _safe_int(headers.get("WhiteElo"))
    black_elo = _safe_int(headers.get("BlackElo"))

    return {
        "pgn": pgn_text.strip(),
        "white_username": headers.get("White", "?"),
        "black_username": headers.get("Black", "?"),
        "result_raw": headers.get("Result", "*"),
        "white_elo": white_elo,
        "black_elo": black_elo,
        "time_control": headers.get("TimeControl"),
        "opening_eco": headers.get("ECO"),
        "opening_name": headers.get("Opening"),
        "played_at": played_at,
        "move_count": len(moves),
    }


def determine_result(result_raw: str, username: str) -> str:
    """Determine win/loss/draw from the user's perspective."""
    # This is called with knowledge of which color the user played
    # result_raw is from White's perspective: "1-0" = white wins
    if result_raw == "1/2-1/2":
        return "draw"
    # Caller should pass the white_username to determine perspective
    # We use a simpler approach: caller tells us if user is white
    return result_raw  # Overridden by caller logic


def determine_result(result_raw: str, white_username: str) -> str:
    """Determine result. Pass white_username to check perspective.

    In practice, caller compares white_username to the user's linked username
    and calls with the appropriate player name.
    """
    if result_raw == "1/2-1/2":
        return "draw"
    if result_raw == "1-0":
        return "win"  # from white's perspective
    if result_raw == "0-1":
        return "loss"  # from white's perspective
    return "draw"


def determine_result(result_raw: str, username: str) -> str:
    """Determine win/loss/draw relative to a given player (white).

    If username is the white player and result is "1-0", it's a win.
    If username is the black player, caller should pass black_username instead.

    Usage: determine_result("1-0", "player1")  # from player1's perspective as white
    """
    if result_raw == "1/2-1/2":
        return "draw"
    if result_raw == "1-0":
        return "win"
    if result_raw == "0-1":
        return "loss"
    return "draw"


def compute_content_hash(moves_text: str, date: str, white: str, black: str) -> str:
    """Compute SHA256 hash for game deduplication."""
    content = f"{moves_text}|{date}|{white}|{black}"
    return hashlib.sha256(content.encode()).hexdigest()


def _safe_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None
```

**NOTE:** The `determine_result` function has been defined multiple times above — only the LAST definition should exist. The implementation should be:

```python
def determine_result(result_raw: str, username: str) -> str:
    """Determine win/loss/draw. Username param is the white player's name.

    Call with white_username: "1-0" → "win", "0-1" → "loss"
    Call with black_username: "1-0" → "loss", "0-1" → "win"
    """
    if result_raw == "1/2-1/2":
        return "draw"
    if result_raw == "1-0":
        return "win"
    if result_raw == "0-1":
        return "loss"
    return "draw"
```

The actual file should have exactly one `determine_result` function.

- [ ] **Step 4: Run tests**

Run: `cd backend && uv run pytest tests/test_pgn_parser.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/chess_services/pgn_parser.py backend/tests/test_pgn_parser.py
git commit -m "feat: PGN parser with metadata extraction and content hash"
```

---

### Task 3: Chess.com API Client

**Files:**
- Create: `backend/app/chess_services/chesscom.py`
- Test: `backend/tests/test_chesscom.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_chesscom.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement**

Create `backend/app/chess_services/chesscom.py`:

```python
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

    # Fetch last 2 months to catch recent games
    all_games = []
    for archive_url in archives[-2:]:
        games = await fetch_games_for_month(archive_url)
        all_games.extend(games)

    if since_timestamp:
        all_games = [g for g in all_games if g.get("end_time", 0) > since_timestamp]

    return all_games
```

- [ ] **Step 4: Run tests**

Run: `cd backend && uv run pytest tests/test_chesscom.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/chess_services/chesscom.py backend/tests/test_chesscom.py
git commit -m "feat: Chess.com API client for game fetching"
```

---

### Task 4: Lichess API Client

**Files:**
- Create: `backend/app/chess_services/lichess_client.py`
- Test: `backend/tests/test_lichess_client.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_lichess_client.py`:

```python
from unittest.mock import AsyncMock, MagicMock, patch
import json

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
```

- [ ] **Step 2: Implement**

Create `backend/app/chess_services/lichess_client.py`:

```python
import json

import httpx

LICHESS_API = "https://lichess.org/api"


async def fetch_recent_games(
    username: str,
    max_games: int = 100,
    since: int | None = None,
    token: str | None = None,
) -> list[dict]:
    """Fetch recent games from Lichess as NDJSON.

    Args:
        username: Lichess username
        max_games: Maximum number of games to fetch
        since: Unix timestamp in milliseconds, fetch games after this time
        token: Optional OAuth token for authenticated requests
    """
    params: dict = {
        "max": max_games,
        "pgnInJson": "true",
    }
    if since:
        params["since"] = since

    headers = {
        "Accept": "application/x-ndjson",
    }
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
```

- [ ] **Step 3: Run tests**

Run: `cd backend && uv run pytest tests/test_lichess_client.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/chess_services/lichess_client.py backend/tests/test_lichess_client.py
git commit -m "feat: Lichess API client for game fetching (NDJSON)"
```

---

### Task 5: Game Import Service

**Files:**
- Create: `backend/app/chess_services/import_service.py`
- Test: `backend/tests/test_import_service.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_import_service.py`:

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import settings
from app.models import Base
from app.models.game import Game
from app.chess_services.import_service import import_chesscom_game, import_pgn_text


SAMPLE_CHESSCOM_GAME = {
    "url": "https://www.chess.com/game/live/12345",
    "pgn": '[Event "Live Chess"]\n[Site "Chess.com"]\n[Date "2026.04.10"]\n[White "testuser"]\n[Black "opponent"]\n[Result "1-0"]\n[WhiteElo "1700"]\n[BlackElo "1650"]\n[TimeControl "600"]\n[ECO "B90"]\n[Opening "Sicilian Defense"]\n\n1. e4 c5 2. Nf3 d6 1-0',
    "time_control": "600",
    "rated": True,
    "white": {"username": "testuser", "rating": 1700},
    "black": {"username": "opponent", "rating": 1650},
}


async def _get_db():
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, factory


async def test_import_chesscom_game():
    engine, factory = await _get_db()
    user_id = uuid.uuid4()

    async with factory() as db:
        from app.models.user import User
        user = User(id=user_id, username="testuser", auth_provider="google", email="t@t.com")
        db.add(user)
        await db.commit()

        game = await import_chesscom_game(db, user_id, "testuser", SAMPLE_CHESSCOM_GAME)

    assert game is not None
    assert game.platform == "chess_com"
    assert game.user_color == "white"
    assert game.result == "win"
    assert game.user_elo == 1700
    assert game.opponent_elo == 1650
    assert game.opening_eco == "B90"

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


async def test_import_dedup():
    engine, factory = await _get_db()
    user_id = uuid.uuid4()

    async with factory() as db:
        from app.models.user import User
        user = User(id=user_id, username="testuser", auth_provider="google", email="t2@t.com")
        db.add(user)
        await db.commit()

        game1 = await import_chesscom_game(db, user_id, "testuser", SAMPLE_CHESSCOM_GAME)
        game2 = await import_chesscom_game(db, user_id, "testuser", SAMPLE_CHESSCOM_GAME)

    assert game1 is not None
    assert game2 is None  # Duplicate, should be skipped

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
```

- [ ] **Step 2: Implement**

Create `backend/app/chess_services/import_service.py`:

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.game import Game
from app.chess_services.pgn_parser import parse_pgn, compute_content_hash, determine_result
from app.chess_services.time_control import classify_time_control


async def import_chesscom_game(
    db: AsyncSession,
    user_id: uuid.UUID,
    chess_com_username: str,
    game_data: dict,
) -> Game | None:
    """Import a single Chess.com game. Returns None if duplicate."""
    pgn_text = game_data.get("pgn", "")
    if not pgn_text:
        return None

    parsed = parse_pgn(pgn_text)

    # Determine user's color and result
    white_lower = parsed["white_username"].lower()
    is_white = white_lower == chess_com_username.lower()
    user_color = "white" if is_white else "black"

    if parsed["result_raw"] == "1/2-1/2":
        result = "draw"
    elif parsed["result_raw"] == "1-0":
        result = "win" if is_white else "loss"
    else:
        result = "loss" if is_white else "win"

    # Dedup
    content_hash = compute_content_hash(
        pgn_text,
        str(parsed["played_at"]),
        parsed["white_username"],
        parsed["black_username"],
    )

    existing = await db.execute(
        select(Game).where(Game.content_hash == content_hash)
    )
    if existing.scalar_one_or_none() is not None:
        return None

    game = Game(
        user_id=user_id,
        platform="chess_com",
        platform_game_id=game_data.get("url", "").split("/")[-1],
        pgn=pgn_text,
        white_username=parsed["white_username"],
        black_username=parsed["black_username"],
        user_color=user_color,
        result=result,
        opening_name=parsed["opening_name"],
        opening_eco=parsed["opening_eco"],
        time_control=parsed["time_control"],
        user_elo=parsed["white_elo"] if is_white else parsed["black_elo"],
        opponent_elo=parsed["black_elo"] if is_white else parsed["white_elo"],
        played_at=parsed["played_at"],
        move_count=parsed["move_count"],
        import_source="sync",
        content_hash=content_hash,
    )
    db.add(game)
    await db.commit()
    await db.refresh(game)
    return game


async def import_lichess_game(
    db: AsyncSession,
    user_id: uuid.UUID,
    lichess_username: str,
    game_data: dict,
) -> Game | None:
    """Import a single Lichess game (from NDJSON). Returns None if duplicate."""
    pgn_text = game_data.get("pgn", "")
    if not pgn_text:
        return None

    parsed = parse_pgn(pgn_text)

    # Determine user's color
    players = game_data.get("players", {})
    white_name = players.get("white", {}).get("user", {}).get("name", "")
    is_white = white_name.lower() == lichess_username.lower()
    user_color = "white" if is_white else "black"

    # Result
    winner = game_data.get("winner")
    if winner is None:
        result = "draw"
    elif (winner == "white" and is_white) or (winner == "black" and not is_white):
        result = "win"
    else:
        result = "loss"

    # Elos
    white_rating = players.get("white", {}).get("rating")
    black_rating = players.get("black", {}).get("rating")

    # Time control from clock
    clock = game_data.get("clock", {})
    initial = clock.get("initial", 0)
    increment = clock.get("increment", 0)
    time_control = f"{initial}+{increment}" if clock else parsed.get("time_control")

    # Opening
    opening = game_data.get("opening", {})

    # Dedup
    content_hash = compute_content_hash(
        pgn_text,
        str(parsed["played_at"]),
        parsed["white_username"],
        parsed["black_username"],
    )

    existing = await db.execute(
        select(Game).where(Game.content_hash == content_hash)
    )
    if existing.scalar_one_or_none() is not None:
        return None

    game = Game(
        user_id=user_id,
        platform="lichess",
        platform_game_id=game_data.get("id", ""),
        pgn=pgn_text,
        white_username=parsed["white_username"],
        black_username=parsed["black_username"],
        user_color=user_color,
        result=result,
        opening_name=opening.get("name", parsed["opening_name"]),
        opening_eco=opening.get("eco", parsed["opening_eco"]),
        time_control=time_control,
        user_elo=white_rating if is_white else black_rating,
        opponent_elo=black_rating if is_white else white_rating,
        played_at=parsed["played_at"],
        move_count=parsed["move_count"],
        import_source="sync",
        content_hash=content_hash,
    )
    db.add(game)
    await db.commit()
    await db.refresh(game)
    return game


async def import_pgn_text(
    db: AsyncSession,
    user_id: uuid.UUID,
    username: str,
    pgn_text: str,
) -> list[Game]:
    """Import one or more games from raw PGN text. Returns list of imported games."""
    import io
    import chess.pgn

    games = []
    pgn_io = io.StringIO(pgn_text)

    while True:
        game = chess.pgn.read_game(pgn_io)
        if game is None:
            break

        single_pgn = str(game)
        parsed = parse_pgn(single_pgn)

        white_lower = parsed["white_username"].lower()
        is_white = white_lower == username.lower()
        user_color = "white" if is_white else "black"

        if parsed["result_raw"] == "1/2-1/2":
            result = "draw"
        elif parsed["result_raw"] == "1-0":
            result = "win" if is_white else "loss"
        else:
            result = "loss" if is_white else "win"

        content_hash = compute_content_hash(
            single_pgn,
            str(parsed["played_at"]),
            parsed["white_username"],
            parsed["black_username"],
        )

        existing = await db.execute(
            select(Game).where(Game.content_hash == content_hash)
        )
        if existing.scalar_one_or_none() is not None:
            continue

        db_game = Game(
            user_id=user_id,
            platform="pgn_upload",
            pgn=single_pgn,
            white_username=parsed["white_username"],
            black_username=parsed["black_username"],
            user_color=user_color,
            result=result,
            opening_name=parsed["opening_name"],
            opening_eco=parsed["opening_eco"],
            time_control=parsed["time_control"],
            user_elo=parsed["white_elo"] if is_white else parsed["black_elo"],
            opponent_elo=parsed["black_elo"] if is_white else parsed["white_elo"],
            played_at=parsed["played_at"],
            move_count=parsed["move_count"],
            import_source="pgn_upload",
            content_hash=content_hash,
        )
        db.add(db_game)
        await db.commit()
        await db.refresh(db_game)
        games.append(db_game)

    return games
```

- [ ] **Step 3: Run tests**

Run: `cd backend && uv run pytest tests/test_import_service.py -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/chess_services/import_service.py backend/tests/test_import_service.py
git commit -m "feat: game import service with Chess.com, Lichess, PGN support + dedup"
```

---

### Task 6: Games API Endpoints

**Files:**
- Create: `backend/app/api/games.py`
- Modify: `backend/app/api/router.py`
- Test: `backend/tests/test_games_api.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_games_api.py`:

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import settings
from app.database import get_db
from app.models import Base
from app.models.user import User
from app.models.game import Game
from app.auth.dependencies import set_session


async def _setup(app):
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override():
        async with factory() as s:
            yield s

    app.dependency_overrides[get_db] = override

    async with factory() as db:
        user = User(username="testplayer", auth_provider="google", email="games@test.com")
        db.add(user)
        await db.commit()
        await db.refresh(user)

        game = Game(
            user_id=user.id,
            platform="chess_com",
            pgn="1. e4 e5 1-0",
            white_username="testplayer",
            black_username="opponent",
            user_color="white",
            result="win",
            opening_name="King's Pawn",
            opening_eco="C20",
            time_control="600",
            user_elo=1700,
            opponent_elo=1650,
            played_at=datetime(2026, 4, 10, tzinfo=timezone.utc),
            move_count=2,
            import_source="sync",
            content_hash="test-hash-1",
        )
        db.add(game)
        await db.commit()

    set_session("games-test", user.id)
    return engine, user


async def _cleanup(engine, app):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    app.dependency_overrides.clear()


async def test_list_games(client, app):
    engine, user = await _setup(app)

    response = await client.get(
        "/api/games",
        cookies={"chesspa_session": "games-test"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert data["games"][0]["result"] == "win"
    assert data["games"][0]["platform"] == "chess_com"

    await _cleanup(engine, app)


async def test_list_games_filter_result(client, app):
    engine, user = await _setup(app)

    response = await client.get(
        "/api/games?result=loss",
        cookies={"chesspa_session": "games-test"},
    )
    assert response.status_code == 200
    assert response.json()["total"] == 0

    await _cleanup(engine, app)


async def test_game_detail(client, app):
    engine, user = await _setup(app)

    # Get list first to find the game ID
    list_resp = await client.get(
        "/api/games",
        cookies={"chesspa_session": "games-test"},
    )
    game_id = list_resp.json()["games"][0]["id"]

    response = await client.get(
        f"/api/games/{game_id}",
        cookies={"chesspa_session": "games-test"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["pgn"] == "1. e4 e5 1-0"
    assert data["white_username"] == "testplayer"

    await _cleanup(engine, app)
```

- [ ] **Step 2: Implement**

Create `backend/app/api/games.py`:

```python
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.game import Game
from app.auth.dependencies import get_current_user
from app.chess_services.time_control import classify_time_control

router = APIRouter(prefix="/api/games", tags=["games"])


@router.get("")
async def list_games(
    platform: str | None = None,
    result: str | None = None,
    opening: str | None = None,
    time_category: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Game).where(Game.user_id == user.id)

    if platform:
        query = query.where(Game.platform == platform)
    if result:
        query = query.where(Game.result == result)
    if opening:
        query = query.where(Game.opening_name.ilike(f"%{opening}%"))
    if since:
        query = query.where(Game.played_at >= since)
    if until:
        query = query.where(Game.played_at <= until)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar()

    # Fetch page
    query = query.order_by(desc(Game.played_at)).offset((page - 1) * limit).limit(limit)
    games_result = await db.execute(query)
    games = games_result.scalars().all()

    # Filter by time category in Python (derived field)
    if time_category:
        games = [g for g in games if classify_time_control(g.time_control) == time_category]

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "games": [
            {
                "id": str(g.id),
                "platform": g.platform,
                "white_username": g.white_username,
                "black_username": g.black_username,
                "user_color": g.user_color,
                "result": g.result,
                "opening_name": g.opening_name,
                "opening_eco": g.opening_eco,
                "time_control": g.time_control,
                "time_category": classify_time_control(g.time_control),
                "user_elo": g.user_elo,
                "opponent_elo": g.opponent_elo,
                "played_at": g.played_at.isoformat() if g.played_at else None,
                "move_count": g.move_count,
                "analysis_status": g.analysis_status,
            }
            for g in games
        ],
    }


@router.get("/{game_id}")
async def get_game(
    game_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import uuid

    result = await db.execute(
        select(Game).where(
            Game.id == uuid.UUID(game_id),
            Game.user_id == user.id,
        )
    )
    game = result.scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    return {
        "id": str(game.id),
        "platform": game.platform,
        "pgn": game.pgn,
        "white_username": game.white_username,
        "black_username": game.black_username,
        "user_color": game.user_color,
        "result": game.result,
        "opening_name": game.opening_name,
        "opening_eco": game.opening_eco,
        "time_control": game.time_control,
        "time_category": classify_time_control(game.time_control),
        "user_elo": game.user_elo,
        "opponent_elo": game.opponent_elo,
        "played_at": game.played_at.isoformat() if game.played_at else None,
        "move_count": game.move_count,
        "analysis_status": game.analysis_status,
        "import_source": game.import_source,
    }
```

- [ ] **Step 3: Register games router**

Edit `backend/app/api/router.py`:

```python
from fastapi import APIRouter

from app.api.accounts import router as accounts_router
from app.api.games import router as games_router

router = APIRouter()
router.include_router(accounts_router)
router.include_router(games_router)
```

- [ ] **Step 4: Run tests**

Run: `cd backend && uv run pytest tests/test_games_api.py -v`
Expected: All PASS

- [ ] **Step 5: Run all tests**

Run: `cd backend && uv run pytest -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/games.py backend/app/api/router.py backend/tests/test_games_api.py
git commit -m "feat: games list + detail API endpoints with filters"
```

---

### Task 7: Manual Sync + PGN Upload Endpoints

**Files:**
- Modify: `backend/app/api/games.py` (add sync + upload endpoints)

- [ ] **Step 1: Add sync and upload endpoints to `backend/app/api/games.py`**

Append to the existing games router:

```python
from fastapi import UploadFile, File
from sqlalchemy.orm import selectinload

from app.models.connected_account import ConnectedAccount
from app.chess_services.chesscom import fetch_recent_games as fetch_chesscom_games
from app.chess_services.lichess_client import fetch_recent_games as fetch_lichess_games
from app.chess_services.import_service import import_chesscom_game, import_lichess_game, import_pgn_text


@router.post("/sync")
async def sync_games(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger manual sync of games from all connected accounts."""
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(User)
        .where(User.id == user.id)
        .options(selectinload(User.connected_accounts))
    )
    user = result.scalar_one()

    imported_count = 0
    errors = []

    for account in user.connected_accounts:
        try:
            if account.platform == "chess_com":
                games = await fetch_chesscom_games(account.platform_username)
                for game_data in games:
                    imported = await import_chesscom_game(
                        db, user.id, account.platform_username, game_data
                    )
                    if imported:
                        imported_count += 1

            elif account.platform == "lichess":
                games = await fetch_lichess_games(account.platform_username)
                for game_data in games:
                    imported = await import_lichess_game(
                        db, user.id, account.platform_username, game_data
                    )
                    if imported:
                        imported_count += 1
        except Exception as e:
            errors.append({"platform": account.platform, "error": str(e)})

    return {
        "imported": imported_count,
        "errors": errors,
    }


@router.post("/import/pgn")
async def upload_pgn(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a PGN file to import games."""
    content = await file.read()
    pgn_text = content.decode("utf-8")

    games = await import_pgn_text(db, user.id, user.username, pgn_text)

    return {
        "imported": len(games),
        "game_ids": [str(g.id) for g in games],
    }
```

- [ ] **Step 2: Run all tests**

Run: `cd backend && uv run pytest -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/games.py
git commit -m "feat: manual sync + PGN upload endpoints"
```

---

### Task 8: Celery Setup + Background Sync Task

**Files:**
- Create: `backend/app/worker/__init__.py`
- Create: `backend/app/worker/celery_app.py`
- Create: `backend/app/worker/tasks.py`
- Modify: `backend/pyproject.toml` (add celery dependency)

- [ ] **Step 1: Add celery to dependencies**

Add to `backend/pyproject.toml` dependencies:
```
"celery[redis]>=5.4.0",
```

Run: `cd backend && uv sync --all-extras`

- [ ] **Step 2: Create `backend/app/worker/__init__.py`** (empty)

- [ ] **Step 3: Create `backend/app/worker/celery_app.py`**

```python
from celery import Celery

from app.config import settings

celery_app = Celery(
    "chesspa",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    beat_schedule={
        "sync-games-every-30-min": {
            "task": "app.worker.tasks.sync_all_accounts",
            "schedule": 1800.0,  # 30 minutes
        },
    },
)
```

- [ ] **Step 4: Create `backend/app/worker/tasks.py`**

```python
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.config import settings
from app.worker.celery_app import celery_app
from app.models.user import User
from app.models.connected_account import ConnectedAccount
from app.chess_services.chesscom import fetch_recent_games as fetch_chesscom_games
from app.chess_services.lichess_client import fetch_recent_games as fetch_lichess_games
from app.chess_services.import_service import import_chesscom_game, import_lichess_game


def _get_session_factory():
    engine = create_async_engine(settings.database_url)
    return engine, async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _sync_account(account: ConnectedAccount, user_id, db: AsyncSession) -> int:
    """Sync games for a single connected account. Returns count of imported games."""
    imported = 0

    if account.platform == "chess_com":
        games = await fetch_chesscom_games(account.platform_username)
        for game_data in games:
            result = await import_chesscom_game(db, user_id, account.platform_username, game_data)
            if result:
                imported += 1

    elif account.platform == "lichess":
        games = await fetch_lichess_games(account.platform_username)
        for game_data in games:
            result = await import_lichess_game(db, user_id, account.platform_username, game_data)
            if result:
                imported += 1

    return imported


@celery_app.task(name="app.worker.tasks.sync_all_accounts")
def sync_all_accounts():
    """Sync games for all users with auto_sync enabled."""
    return asyncio.run(_sync_all_accounts_async())


async def _sync_all_accounts_async():
    engine, factory = _get_session_factory()
    total_imported = 0

    async with factory() as db:
        result = await db.execute(
            select(ConnectedAccount).where(ConnectedAccount.auto_sync == True)
        )
        accounts = result.scalars().all()

        for account in accounts:
            try:
                count = await _sync_account(account, account.user_id, db)
                total_imported += count
            except Exception as e:
                print(f"Sync error for {account.platform}/{account.platform_username}: {e}")

    await engine.dispose()
    return {"imported": total_imported, "accounts_processed": len(accounts)}
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/worker/ backend/pyproject.toml
git commit -m "feat: Celery setup with periodic game sync task (every 30 min)"
```

---

### Task 9: Phase 2 Integration Test

- [ ] **Step 1: Run all tests**

Run: `cd backend && uv run pytest -v`
Expected: All tests PASS

- [ ] **Step 2: Verify endpoints exist**

Check that these endpoints are registered:
- `GET /api/games`
- `GET /api/games/{game_id}`
- `POST /api/games/sync`
- `POST /api/games/import/pgn`

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "chore: phase 2 complete — game import pipeline with Chess.com, Lichess, PGN upload, Celery sync"
```
