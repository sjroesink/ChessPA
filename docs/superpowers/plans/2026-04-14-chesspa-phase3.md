# ChessPA Phase 3: Stockfish Analysis Pipeline

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Analyze every imported game move-by-move using Stockfish, classify moves, compute game summaries with phase detection, and expose analysis results via API.

**Architecture:** Stockfish runs as UCI subprocess via python-chess. Analysis is triggered as a Celery task after game import. Each move gets an eval (centipawns), best move, and classification. Game summaries aggregate stats per phase (opening/middlegame/endgame).

**Tech Stack:** python-chess (UCI), Stockfish binary, Celery, SQLAlchemy async

**Spec:** `docs/superpowers/specs/2026-04-13-chesspa-design.md`

---

## File Structure

```
backend/
├── app/
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── stockfish.py        # Stockfish engine wrapper
│   │   ├── analyzer.py         # Move-by-move analysis logic
│   │   ├── classifier.py       # Move classification by centipawn loss
│   │   └── summary.py          # Game summary computation (phases, stats)
│   ├── api/
│   │   ├── analysis.py         # /api/games/:id/analysis endpoint
│   │   └── router.py           # (modify: add analysis router)
│   └── worker/
│       └── tasks.py            # (modify: add analyze_game task)
├── tests/
│   ├── test_classifier.py
│   ├── test_summary.py
│   ├── test_analyzer.py
│   └── test_analysis_api.py
```

---

### Task 1: Move Classifier

**Files:**
- Create: `backend/app/analysis/__init__.py`
- Create: `backend/app/analysis/classifier.py`
- Test: `backend/tests/test_classifier.py`

- [ ] **Step 1: Write tests**

Create `backend/app/analysis/__init__.py` (empty).

Create `backend/tests/test_classifier.py`:

```python
from app.analysis.classifier import classify_move


def test_best_move():
    assert classify_move(0) == "best"
    assert classify_move(5) == "best"
    assert classify_move(10) == "best"


def test_good_move():
    assert classify_move(11) == "good"
    assert classify_move(20) == "good"
    assert classify_move(25) == "good"


def test_inaccuracy():
    assert classify_move(26) == "inaccuracy"
    assert classify_move(40) == "inaccuracy"
    assert classify_move(50) == "inaccuracy"


def test_mistake():
    assert classify_move(51) == "mistake"
    assert classify_move(75) == "mistake"
    assert classify_move(100) == "mistake"


def test_blunder():
    assert classify_move(101) == "blunder"
    assert classify_move(200) == "blunder"
    assert classify_move(500) == "blunder"
```

- [ ] **Step 2: Implement**

Create `backend/app/analysis/classifier.py`:

```python
def classify_move(centipawn_loss: float) -> str:
    """Classify a move based on centipawn loss (absolute value).

    Thresholds:
      best:       <= 10 cp
      good:       <= 25 cp
      inaccuracy: <= 50 cp
      mistake:    <= 100 cp
      blunder:    > 100 cp
    """
    cp = abs(centipawn_loss)
    if cp <= 10:
        return "best"
    elif cp <= 25:
        return "good"
    elif cp <= 50:
        return "inaccuracy"
    elif cp <= 100:
        return "mistake"
    else:
        return "blunder"
```

- [ ] **Step 3: Run tests, commit**

Run: `cd backend && uv run pytest tests/test_classifier.py -v`
Commit: `feat: move classifier by centipawn loss thresholds`

---

### Task 2: Game Summary Computation

**Files:**
- Create: `backend/app/analysis/summary.py`
- Test: `backend/tests/test_summary.py`

- [ ] **Step 1: Write tests**

Create `backend/tests/test_summary.py`:

```python
from app.analysis.summary import compute_game_summary, detect_phase


def test_detect_phase():
    assert detect_phase(1, 40) == "opening"
    assert detect_phase(10, 40) == "opening"
    assert detect_phase(11, 40) == "middlegame"
    assert detect_phase(30, 40) == "middlegame"
    assert detect_phase(35, 40) == "endgame"
    assert detect_phase(40, 40) == "endgame"


def test_compute_game_summary():
    move_analyses = [
        {"classification": "best", "eval_loss": 2, "move_number": 1, "total_moves": 30},
        {"classification": "good", "eval_loss": 15, "move_number": 5, "total_moves": 30},
        {"classification": "blunder", "eval_loss": 150, "move_number": 15, "total_moves": 30},
        {"classification": "mistake", "eval_loss": 80, "move_number": 20, "total_moves": 30},
        {"classification": "inaccuracy", "eval_loss": 40, "move_number": 28, "total_moves": 30},
    ]

    summary = compute_game_summary(move_analyses)
    assert summary["blunders"] == 1
    assert summary["mistakes"] == 1
    assert summary["inaccuracies"] == 1
    assert summary["avg_eval_loss"] > 0
    assert "opening" in summary["phase_scores"]
    assert "middlegame" in summary["phase_scores"]
    assert "endgame" in summary["phase_scores"]


def test_compute_game_summary_empty():
    summary = compute_game_summary([])
    assert summary["blunders"] == 0
    assert summary["mistakes"] == 0
    assert summary["avg_eval_loss"] == 0.0
```

- [ ] **Step 2: Implement**

Create `backend/app/analysis/summary.py`:

```python
def detect_phase(move_number: int, total_moves: int) -> str:
    """Detect game phase based on move number.

    opening:    first 25% of moves
    middlegame: 25% - 75%
    endgame:    last 25%
    """
    if total_moves == 0:
        return "opening"
    ratio = move_number / total_moves
    if ratio <= 0.25:
        return "opening"
    elif ratio <= 0.75:
        return "middlegame"
    else:
        return "endgame"


def compute_game_summary(move_analyses: list[dict]) -> dict:
    """Compute aggregate statistics from a list of move analyses.

    Each item in move_analyses should have:
      classification, eval_loss, move_number, total_moves
    """
    if not move_analyses:
        return {
            "blunders": 0,
            "mistakes": 0,
            "inaccuracies": 0,
            "avg_eval_loss": 0.0,
            "phase_scores": {"opening": 100, "middlegame": 100, "endgame": 100},
            "time_trouble": False,
        }

    blunders = sum(1 for m in move_analyses if m["classification"] == "blunder")
    mistakes = sum(1 for m in move_analyses if m["classification"] == "mistake")
    inaccuracies = sum(1 for m in move_analyses if m["classification"] == "inaccuracy")
    avg_eval_loss = sum(m["eval_loss"] for m in move_analyses) / len(move_analyses)

    # Phase scores: average accuracy per phase (100 - avg_eval_loss)
    phase_moves: dict[str, list[float]] = {"opening": [], "middlegame": [], "endgame": []}
    for m in move_analyses:
        phase = detect_phase(m["move_number"], m["total_moves"])
        phase_moves[phase].append(m["eval_loss"])

    phase_scores = {}
    for phase, losses in phase_moves.items():
        if losses:
            avg_loss = sum(losses) / len(losses)
            phase_scores[phase] = max(0, round(100 - avg_loss, 1))
        else:
            phase_scores[phase] = 100

    return {
        "blunders": blunders,
        "mistakes": mistakes,
        "inaccuracies": inaccuracies,
        "avg_eval_loss": round(avg_eval_loss, 2),
        "phase_scores": phase_scores,
        "time_trouble": False,  # Will be enhanced when time data is available
    }
```

- [ ] **Step 3: Run tests, commit**

Run: `cd backend && uv run pytest tests/test_summary.py -v`
Commit: `feat: game summary computation with phase detection`

---

### Task 3: Stockfish Engine Wrapper

**Files:**
- Create: `backend/app/analysis/stockfish.py`

- [ ] **Step 1: Implement**

Create `backend/app/analysis/stockfish.py`:

```python
import chess
import chess.engine
from dataclasses import dataclass


@dataclass
class MoveEval:
    move_san: str
    eval_before: float  # centipawns, from white's perspective
    eval_after: float
    best_move_san: str
    centipawn_loss: float


async def analyze_position(
    engine: chess.engine.SimpleEngine,
    board: chess.Board,
    move: chess.Move,
    depth: int = 20,
) -> MoveEval:
    """Analyze a single move: get eval before, eval after, and best move."""
    # Eval before the move
    info_before = engine.analyse(board, chess.engine.Limit(depth=depth))
    eval_before = _score_to_cp(info_before["score"], board.turn)

    # Get best move
    best_move = info_before.get("pv", [None])[0]
    best_move_san = board.san(best_move) if best_move else board.san(move)

    # Make the move and eval after
    move_san = board.san(move)
    board.push(move)
    info_after = engine.analyse(board, chess.engine.Limit(depth=depth))
    eval_after = _score_to_cp(info_after["score"], board.turn)
    board.pop()

    # Centipawn loss (from the moving side's perspective)
    # eval_before is from the perspective of the side to move
    # eval_after is from the perspective of the OTHER side (after move, it's opponent's turn)
    # So: loss = eval_before - (-eval_after) = eval_before + eval_after
    # But we need to normalize: both evals should be from White's perspective
    if board.turn == chess.WHITE:
        cp_before = eval_before
        cp_after = -eval_after  # flip because after move it's Black's perspective
    else:
        cp_before = -eval_before  # Black's perspective, flip to White's
        cp_after = eval_after  # after Black's move, it's White's turn

    centipawn_loss = abs(cp_before - cp_after)

    return MoveEval(
        move_san=move_san,
        eval_before=cp_before,
        eval_after=cp_after,
        best_move_san=best_move_san,
        centipawn_loss=centipawn_loss,
    )


def _score_to_cp(score: chess.engine.PovScore, turn: chess.Color) -> float:
    """Convert engine score to centipawns from the side-to-move's perspective."""
    relative = score.relative
    if relative.is_mate():
        mate_in = relative.mate()
        # Large value for mate: positive if winning, negative if losing
        return 10000 if mate_in > 0 else -10000
    return float(relative.score(mate_score=10000))


def open_engine(path: str = "stockfish", threads: int = 2, hash_mb: int = 256) -> chess.engine.SimpleEngine:
    """Open a Stockfish engine instance."""
    engine = chess.engine.SimpleEngine.popen_uci(path)
    engine.configure({"Threads": threads, "Hash": hash_mb})
    return engine
```

- [ ] **Step 2: Commit**

No tests for this module (requires Stockfish binary). Tested via analyzer integration.
Commit: `feat: Stockfish engine wrapper with position analysis`

---

### Task 4: Game Analyzer

**Files:**
- Create: `backend/app/analysis/analyzer.py`
- Test: `backend/tests/test_analyzer.py`

- [ ] **Step 1: Write tests (mock Stockfish)**

Create `backend/tests/test_analyzer.py`:

```python
from unittest.mock import MagicMock, patch
import uuid

from app.analysis.analyzer import analyze_game_moves
from app.analysis.stockfish import MoveEval


SAMPLE_PGN = "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0"


def test_analyze_game_moves():
    # Mock the engine and analyze_position
    mock_evals = [
        MoveEval("e4", 0, 20, "e4", 0),
        MoveEval("e5", 20, 15, "e5", 5),
        MoveEval("Nf3", 15, 30, "Nf3", 0),
        MoveEval("Nc6", 30, 25, "Nc6", 5),
        MoveEval("Bb5", 25, 60, "Bb5", 0),
        MoveEval("a6", 60, 45, "a6", 15),
    ]

    with patch("app.analysis.analyzer.analyze_position") as mock_analyze:
        mock_analyze.side_effect = mock_evals
        mock_engine = MagicMock()

        results = analyze_game_moves(mock_engine, SAMPLE_PGN, depth=20)

    assert len(results) == 6
    assert results[0]["move_san"] == "e4"
    assert results[0]["move_number"] == 1
    assert results[0]["color"] == "white"
    assert results[1]["color"] == "black"
    assert results[5]["move_number"] == 3
    assert "classification" in results[0]
```

- [ ] **Step 2: Implement**

Create `backend/app/analysis/analyzer.py`:

```python
import io

import chess
import chess.pgn

from app.analysis.stockfish import analyze_position, MoveEval
from app.analysis.classifier import classify_move


def analyze_game_moves(
    engine,
    pgn_text: str,
    depth: int = 20,
) -> list[dict]:
    """Analyze all moves in a game and return per-move analysis data."""
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        return []

    board = game.board()
    moves = list(game.mainline_moves())
    total_moves = (len(moves) + 1) // 2  # full moves
    results = []

    for i, move in enumerate(moves):
        move_number = (i // 2) + 1
        color = "white" if i % 2 == 0 else "black"

        eval_result: MoveEval = analyze_position(engine, board, move, depth)

        classification = classify_move(eval_result.centipawn_loss)

        results.append({
            "move_number": move_number,
            "color": color,
            "move_san": eval_result.move_san,
            "eval_before": eval_result.eval_before,
            "eval_after": eval_result.eval_after,
            "best_move_san": eval_result.best_move_san,
            "classification": classification,
            "centipawn_loss": eval_result.centipawn_loss,
            "total_moves": total_moves,
        })

        board.push(move)

    return results
```

- [ ] **Step 3: Run tests, commit**

Run: `cd backend && uv run pytest tests/test_analyzer.py -v`
Commit: `feat: game analyzer with move-by-move Stockfish analysis`

---

### Task 5: Analysis Celery Task + DB Persistence

**Files:**
- Modify: `backend/app/worker/tasks.py` (add analyze_game task)

- [ ] **Step 1: Add analyze_game task**

Add to `backend/app/worker/tasks.py`:

```python
from app.models.game import Game
from app.models.move_analysis import MoveAnalysis
from app.models.game_summary import GameSummary
from app.analysis.analyzer import analyze_game_moves
from app.analysis.stockfish import open_engine
from app.analysis.summary import compute_game_summary


@celery_app.task(name="app.worker.tasks.analyze_game")
def analyze_game(game_id: str):
    """Analyze a single game with Stockfish and persist results."""
    return asyncio.run(_analyze_game_async(game_id))


async def _analyze_game_async(game_id: str):
    import uuid

    engine_instance = None
    engine_db, factory = _get_session_factory()

    try:
        async with factory() as db:
            result = await db.execute(
                select(Game).where(Game.id == uuid.UUID(game_id))
            )
            game = result.scalar_one_or_none()
            if game is None:
                return {"error": "Game not found"}

            if game.analysis_status == "done":
                return {"status": "already_analyzed"}

            # Update status
            game.analysis_status = "analyzing"
            await db.commit()

            # Run Stockfish analysis
            try:
                engine_instance = open_engine()
                move_results = analyze_game_moves(engine_instance, game.pgn)
            except Exception as e:
                game.analysis_status = "failed"
                await db.commit()
                return {"error": str(e)}

            # Persist move analyses
            for mr in move_results:
                ma = MoveAnalysis(
                    game_id=game.id,
                    move_number=mr["move_number"],
                    color=mr["color"],
                    move_san=mr["move_san"],
                    eval_before=mr["eval_before"],
                    eval_after=mr["eval_after"],
                    best_move_san=mr["best_move_san"],
                    classification=mr["classification"],
                )
                db.add(ma)

            # Compute and persist summary
            summary_input = [
                {
                    "classification": mr["classification"],
                    "eval_loss": mr["centipawn_loss"],
                    "move_number": mr["move_number"],
                    "total_moves": mr["total_moves"],
                }
                for mr in move_results
            ]
            summary_data = compute_game_summary(summary_input)

            game_summary = GameSummary(
                game_id=game.id,
                blunders=summary_data["blunders"],
                mistakes=summary_data["mistakes"],
                inaccuracies=summary_data["inaccuracies"],
                avg_eval_loss=summary_data["avg_eval_loss"],
                phase_scores=summary_data["phase_scores"],
                time_trouble=summary_data["time_trouble"],
            )
            db.add(game_summary)

            game.analysis_status = "done"
            await db.commit()

            return {
                "status": "done",
                "moves_analyzed": len(move_results),
                "blunders": summary_data["blunders"],
            }
    finally:
        if engine_instance:
            engine_instance.quit()
        await engine_db.dispose()
```

- [ ] **Step 2: Commit**

Commit: `feat: Stockfish analysis Celery task with DB persistence`

---

### Task 6: Analysis API Endpoint

**Files:**
- Create: `backend/app/api/analysis.py`
- Modify: `backend/app/api/router.py`
- Test: `backend/tests/test_analysis_api.py`

- [ ] **Step 1: Write tests**

Create `backend/tests/test_analysis_api.py`:

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import settings
from app.database import get_db
from app.models import Base
from app.models.user import User
from app.models.game import Game
from app.models.move_analysis import MoveAnalysis
from app.models.game_summary import GameSummary
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
        user = User(username="analyst", auth_provider="google", email="analysis@test.com")
        db.add(user)
        await db.commit()
        await db.refresh(user)

        game = Game(
            user_id=user.id,
            platform="chess_com",
            pgn="1. e4 e5 1-0",
            white_username="analyst",
            black_username="opponent",
            user_color="white",
            result="win",
            time_control="600",
            played_at=datetime(2026, 4, 10, tzinfo=timezone.utc),
            move_count=2,
            import_source="sync",
            content_hash="analysis-test-hash",
            analysis_status="done",
        )
        db.add(game)
        await db.commit()
        await db.refresh(game)

        ma = MoveAnalysis(
            game_id=game.id,
            move_number=1,
            color="white",
            move_san="e4",
            eval_before=0.0,
            eval_after=20.0,
            best_move_san="e4",
            classification="best",
        )
        db.add(ma)

        gs = GameSummary(
            game_id=game.id,
            blunders=0,
            mistakes=0,
            inaccuracies=0,
            avg_eval_loss=5.0,
            phase_scores={"opening": 95, "middlegame": 90, "endgame": 85},
            time_trouble=False,
        )
        db.add(gs)
        await db.commit()

    set_session("analysis-test", user.id)
    return engine, user, game


async def _cleanup(engine, app):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    app.dependency_overrides.clear()


async def test_get_analysis(client, app):
    engine, user, game = await _setup(app)

    response = await client.get(
        f"/api/games/{game.id}/analysis",
        cookies={"chesspa_session": "analysis-test"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["blunders"] == 0
    assert data["summary"]["avg_eval_loss"] == 5.0
    assert len(data["moves"]) == 1
    assert data["moves"][0]["move_san"] == "e4"
    assert data["moves"][0]["classification"] == "best"

    await _cleanup(engine, app)


async def test_get_analysis_not_found(client, app):
    engine, user, game = await _setup(app)

    fake_id = str(uuid.uuid4())
    response = await client.get(
        f"/api/games/{fake_id}/analysis",
        cookies={"chesspa_session": "analysis-test"},
    )
    assert response.status_code == 404

    await _cleanup(engine, app)
```

- [ ] **Step 2: Implement**

Create `backend/app/api/analysis.py`:

```python
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.user import User
from app.models.game import Game
from app.models.move_analysis import MoveAnalysis
from app.models.game_summary import GameSummary
from app.auth.dependencies import get_current_user

router = APIRouter(tags=["analysis"])


@router.get("/api/games/{game_id}/analysis")
async def get_analysis(
    game_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Game).where(
            Game.id == uuid.UUID(game_id),
            Game.user_id == user.id,
        )
    )
    game = result.scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    # Fetch move analyses
    moves_result = await db.execute(
        select(MoveAnalysis)
        .where(MoveAnalysis.game_id == game.id)
        .order_by(MoveAnalysis.move_number, MoveAnalysis.color)
    )
    moves = moves_result.scalars().all()

    # Fetch summary
    summary_result = await db.execute(
        select(GameSummary).where(GameSummary.game_id == game.id)
    )
    summary = summary_result.scalar_one_or_none()

    return {
        "game_id": str(game.id),
        "analysis_status": game.analysis_status,
        "moves": [
            {
                "move_number": m.move_number,
                "color": m.color,
                "move_san": m.move_san,
                "eval_before": m.eval_before,
                "eval_after": m.eval_after,
                "best_move_san": m.best_move_san,
                "classification": m.classification,
            }
            for m in moves
        ],
        "summary": {
            "blunders": summary.blunders,
            "mistakes": summary.mistakes,
            "inaccuracies": summary.inaccuracies,
            "avg_eval_loss": summary.avg_eval_loss,
            "phase_scores": summary.phase_scores,
            "time_trouble": summary.time_trouble,
        } if summary else None,
    }
```

- [ ] **Step 3: Register in router**

Edit `backend/app/api/router.py` to include:
```python
from app.api.analysis import router as analysis_router
router.include_router(analysis_router)
```

- [ ] **Step 4: Run tests, commit**

Run: `cd backend && uv run pytest tests/test_analysis_api.py -v`
Run: `cd backend && uv run pytest -v`
Commit: `feat: analysis API endpoint for move-by-move results + game summary`

---

### Task 7: Auto-trigger Analysis on Import

**Files:**
- Modify: `backend/app/chess_services/import_service.py`

- [ ] **Step 1: Add analysis trigger after successful import**

In each import function (import_chesscom_game, import_lichess_game, import_pgn_text), after a game is successfully saved, dispatch the analyze_game Celery task:

```python
from app.worker.tasks import analyze_game

# After db.commit() and db.refresh(game):
analyze_game.delay(str(game.id))
```

NOTE: Use try/except around the .delay() call so import doesn't fail if Celery/Redis is down. The game still gets saved; analysis can be triggered later.

- [ ] **Step 2: Run all tests**

Run: `cd backend && uv run pytest -v`
Expected: All pass (Celery task dispatch is mocked/skipped in test env since Redis may not be connected)

- [ ] **Step 3: Commit**

Commit: `feat: auto-trigger Stockfish analysis on game import`
