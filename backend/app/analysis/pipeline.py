"""Progressive analysis pipeline with priority queue + focus preemption.

An AnalysisSession owns one in-progress analysis of one game. It:
  1. inspects existing MoveAnalysis rows to know which (ply, stage) units are
     still missing,
  2. schedules those units with priorities that honour the user's current
     focus ply (deep/enrich for focus first, then shallow scan of the rest,
     then standard pass, then deep/enrich for everyone on request),
  3. borrows a Stockfish engine from the global pool and runs one unit at a
     time,
  4. emits events (via an async emitter) so the caller (WebSocket handler,
     Celery task) can relay them to the client or just ignore them,
  5. persists each completed unit to the DB.

Preemption: when the caller flips the focus ply, the currently-running unit
is cancelled via its asyncio Event; the pipeline re-evaluates priorities and
starts the new focus unit immediately.
"""

from __future__ import annotations

import asyncio
import heapq
import io
import logging
import uuid
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Iterable

import chess
import chess.pgn
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.engine_pool import EnginePool, get_pool
from app.analysis.scoring import (
    accuracy_from_win_delta,
    label_from_win_drop,
    win_percent_from_cp,
)
from app.analysis.stages import (
    ALL_STAGES,
    StageName,
    mark_stage_complete,
    missing_stages,
)
from app.analysis.stream import StageRunResult, run_stage
from app.config import settings
from app.models.game import Game
from app.models.move_analysis import MoveAnalysis

logger = logging.getLogger(__name__)

Emitter = Callable[[dict], Awaitable[None]]


_PRIORITY_FOCUS_DEEP = 0
_PRIORITY_FOCUS_ENRICH = 1
_PRIORITY_NEIGHBOUR_ENRICH = 2
_PRIORITY_SHALLOW_GAP = 3
_PRIORITY_STANDARD_GAP = 4
_PRIORITY_BULK_DEEP = 5
_PRIORITY_BULK_ENRICH = 6


@dataclass(order=True)
class _QueueEntry:
    priority: int
    seq: int
    ply: int = field(compare=False)
    stage: StageName = field(compare=False)


@dataclass
class _PlyContext:
    ply: int
    move_number: int
    color: str
    move_san: str
    move_uci: str
    fen_before: str
    played_move: chess.Move
    board_before: chess.Board


class AnalysisSession:
    def __init__(
        self,
        db: AsyncSession,
        game: Game,
        pool: EnginePool | None = None,
        emitter: Emitter | None = None,
    ):
        self.db = db
        self.game = game
        self._pool = pool
        self._emit = emitter
        self._plies: list[_PlyContext] = []
        self._rows: dict[int, MoveAnalysis] = {}  # ply index -> row
        self._queue: list[_QueueEntry] = []
        self._seq = 0
        self._focus_ply: int | None = None
        self._cancel_current: asyncio.Event = asyncio.Event()
        self._desired_stages: tuple[StageName, ...] = ALL_STAGES
        self._deep_all: bool = False
        self._loaded = False

    # ------------------------------------------------------------------
    # Loading / scheduling
    # ------------------------------------------------------------------

    async def load(self) -> None:
        """Parse PGN to ply contexts, fetch existing MoveAnalysis rows."""
        if self._loaded:
            return
        pgn_game = chess.pgn.read_game(io.StringIO(self.game.pgn))
        if pgn_game is None:
            self._loaded = True
            return
        board = pgn_game.board()
        for i, move in enumerate(pgn_game.mainline_moves()):
            move_number = (i // 2) + 1
            color = "white" if i % 2 == 0 else "black"
            ctx = _PlyContext(
                ply=i,
                move_number=move_number,
                color=color,
                move_san=board.san(move),
                move_uci=move.uci(),
                fen_before=board.fen(),
                played_move=move,
                board_before=board.copy(stack=False),
            )
            self._plies.append(ctx)
            board.push(move)

        result = await self.db.execute(
            select(MoveAnalysis).where(MoveAnalysis.game_id == self.game.id)
        )
        existing = result.scalars().all()
        by_key: dict[tuple[int, str], MoveAnalysis] = {
            (r.move_number, r.color): r for r in existing
        }
        for ctx in self._plies:
            row = by_key.get((ctx.move_number, ctx.color))
            if row is not None:
                self._rows[ctx.ply] = row
        self._loaded = True

    def total_plies(self) -> int:
        return len(self._plies)

    def set_desired_stages(self, stages: Iterable[StageName]) -> None:
        ordered = tuple(s for s in ALL_STAGES if s in tuple(stages))
        self._desired_stages = ordered or ALL_STAGES

    def set_deep_all(self, enabled: bool) -> None:
        self._deep_all = enabled
        self._rebuild_queue()

    def set_focus(self, ply: int | None) -> None:
        self._focus_ply = ply
        # interrupt current work so the loop can re-pick with new priorities
        self._cancel_current.set()
        self._rebuild_queue()

    def _missing_for_ply(self, ply: int) -> list[StageName]:
        row = self._rows.get(ply)
        completed = row.completed_stages if row and row.completed_stages else []
        return missing_stages(completed, self._desired_stages)

    def _rebuild_queue(self) -> None:
        self._queue = []
        self._seq = 0
        for ctx in self._plies:
            missing = self._missing_for_ply(ctx.ply)
            for stage in missing:
                priority = self._priority(ctx.ply, stage)
                if priority is None:
                    continue
                self._seq += 1
                heapq.heappush(
                    self._queue,
                    _QueueEntry(priority=priority, seq=self._seq, ply=ctx.ply, stage=stage),
                )

    def _priority(self, ply: int, stage: StageName) -> int | None:
        if self._focus_ply is not None and ply == self._focus_ply:
            if stage == "deep":
                return _PRIORITY_FOCUS_DEEP
            if stage == "enrich":
                return _PRIORITY_FOCUS_ENRICH
            if stage == "standard":
                return _PRIORITY_FOCUS_DEEP + 1  # just after focus-deep
            if stage == "shallow":
                return _PRIORITY_FOCUS_DEEP  # also burst shallow on focus
        if (
            self._focus_ply is not None
            and stage == "enrich"
            and 1 <= abs(ply - self._focus_ply) <= 3
        ):
            return _PRIORITY_NEIGHBOUR_ENRICH
        if stage == "shallow":
            return _PRIORITY_SHALLOW_GAP
        if stage == "standard":
            return _PRIORITY_STANDARD_GAP
        if stage == "deep":
            return _PRIORITY_BULK_DEEP if self._deep_all else None
        if stage == "enrich":
            return _PRIORITY_BULK_ENRICH if self._deep_all else None
        return None

    def _pop_next(self) -> _QueueEntry | None:
        while self._queue:
            entry = heapq.heappop(self._queue)
            # re-validate against current completed state + priority rules
            still_missing = entry.stage in self._missing_for_ply(entry.ply)
            still_prio = self._priority(entry.ply, entry.stage)
            if still_missing and still_prio is not None:
                return entry
        return None

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def run(self, stop_event: asyncio.Event | None = None) -> None:
        """Process queue until empty or stop_event is set."""
        if not self._loaded:
            await self.load()
        self._rebuild_queue()
        pool = self._pool or get_pool()

        while True:
            if stop_event is not None and stop_event.is_set():
                return
            entry = self._pop_next()
            if entry is None:
                # nothing to do
                return
            await self._run_unit(entry, pool, stop_event)

    async def _run_unit(
        self,
        entry: _QueueEntry,
        pool: EnginePool,
        stop_event: asyncio.Event | None,
    ) -> None:
        ctx = self._plies[entry.ply]
        self._cancel_current = asyncio.Event()
        async with pool.acquire() as engine:
            if entry.stage == "enrich":
                await self._run_enrich(ctx, engine)
            else:
                await self._run_engine_stage(ctx, entry.stage, engine)

        if self._cancel_current.is_set():
            # Preempted: leave completed_stages unchanged; re-schedule later.
            logger.debug("preempted ply=%d stage=%s", ctx.ply, entry.stage)
            self._rebuild_queue()

    async def _run_engine_stage(
        self,
        ctx: _PlyContext,
        stage: StageName,
        engine,
    ) -> None:
        before = await run_stage(engine, ctx.board_before, stage, cancel_event=self._cancel_current)
        if before.stopped_early and not before.multipv:
            return

        # Analyse position after the played move at the same stage budget for
        # eval_after. Side-to-move flips, so negate back into the mover's frame.
        after_board = ctx.board_before.copy(stack=False)
        after_board.push(ctx.played_move)
        after = await run_stage(engine, after_board, stage, cancel_event=self._cancel_current)

        eval_before_cp = before.multipv[0].eval_cp if before.multipv else 0.0
        eval_after_stm = -after.multipv[0].eval_cp if after.multipv else eval_before_cp

        win_before = win_percent_from_cp(eval_before_cp)
        win_after = win_percent_from_cp(eval_after_stm)
        win_drop = max(0.0, win_before - win_after)
        drop_label = label_from_win_drop(win_drop)
        best_san = before.multipv[0].san if before.multipv else ctx.move_san
        classification = drop_label or ("best" if ctx.move_san == best_san else "ok")
        cpl = max(0.0, eval_before_cp - eval_after_stm)

        gap = 0.0
        if len(before.multipv) >= 2:
            gap = before.multipv[0].eval_cp - before.multipv[1].eval_cp
        is_critical = gap >= settings.critical_moment_cp_gap

        row = self._rows.get(ctx.ply)
        if row is None:
            row = MoveAnalysis(
                game_id=self.game.id,
                move_number=ctx.move_number,
                color=ctx.color,
                move_san=ctx.move_san,
                eval_before=eval_before_cp,
                eval_after=eval_after_stm,
                best_move_san=best_san,
                classification=classification,
                fen=ctx.fen_before,
            )
            self.db.add(row)
            self._rows[ctx.ply] = row

        # Always refresh these so later stages overwrite shallow results.
        row.eval_before = eval_before_cp
        row.eval_after = eval_after_stm
        row.best_move_san = best_san
        row.classification = classification
        row.fen = ctx.fen_before
        row.win_percent_before = win_before
        row.win_percent_after = win_after
        row.accuracy_percent = accuracy_from_win_delta(win_drop)
        row.is_critical_moment = is_critical

        details = dict(row.details_json or {})
        details["multipv"] = [pv.as_dict() for pv in before.multipv]
        # keep any previously computed motifs/features if enrich already ran
        row.details_json = details

        row.completed_stages = mark_stage_complete(row.completed_stages, stage)

        await self.db.flush()
        await self.db.commit()

        await self._emit_event(
            {
                "type": "ply",
                "ply": ctx.ply,
                "stage": stage,
                "data": {
                    "move_number": ctx.move_number,
                    "color": ctx.color,
                    "move_san": ctx.move_san,
                    "best_move_san": best_san,
                    "classification": classification,
                    "eval_before": eval_before_cp,
                    "eval_after": eval_after_stm,
                    "centipawn_loss": cpl,
                    "win_percent_before": win_before,
                    "win_percent_after": win_after,
                    "accuracy_percent": row.accuracy_percent,
                    "is_critical_moment": is_critical,
                    "multipv": details["multipv"],
                    "completed_stages": row.completed_stages,
                    "fen": ctx.fen_before,
                },
            }
        )

    async def _run_enrich(self, ctx: _PlyContext, engine) -> None:
        # Deferred import to avoid loading LLM deps when not needed.
        from app.analysis.commentary import generate_single_comment
        from app.analysis.facts import build_move_fact_bundle
        from app.analysis.motifs import detect_geometric_motifs, verify_motifs
        from app.analysis.positional import extract_features

        row = self._rows.get(ctx.ply)
        if row is None:
            return  # standard must have run first; skip quietly

        board = ctx.board_before.copy(stack=False)
        geo = detect_geometric_motifs(board) if settings.enable_motifs else []
        verified = verify_motifs(engine, board, geo) if geo else []
        features = extract_features(board)

        details = dict(row.details_json or {})
        details["motifs"] = verified
        details["features"] = features
        row.details_json = details

        # LLM commentary (single call per move)
        move_row_dict = {
            "move_number": ctx.move_number,
            "color": ctx.color,
            "move_san": ctx.move_san,
            "move_uci": ctx.move_uci,
            "fen": ctx.fen_before,
            "eval_before": row.eval_before,
            "eval_after": row.eval_after,
            "centipawn_loss": max(0.0, row.eval_before - row.eval_after)
            if row.eval_before is not None and row.eval_after is not None
            else 0.0,
            "win_percent_before": row.win_percent_before,
            "win_percent_after": row.win_percent_after,
            "accuracy_percent": row.accuracy_percent,
            "classification": row.classification,
            "best_move_san": row.best_move_san,
            "is_critical_moment": row.is_critical_moment,
            "multipv": details.get("multipv", []),
        }
        bundle = build_move_fact_bundle(move_row_dict, self.game.user_color, verified, features)
        try:
            if row.classification in ("blunder", "mistake", "inaccuracy") or row.is_critical_moment:
                comment = await generate_single_comment(bundle, self.game.user_color)
                if comment:
                    row.comment = comment
        except Exception as exc:  # pragma: no cover
            logger.warning("enrich commentary failed ply=%d: %s", ctx.ply, exc)

        row.completed_stages = mark_stage_complete(row.completed_stages, "enrich")
        await self.db.flush()
        await self.db.commit()

        await self._emit_event(
            {
                "type": "ply",
                "ply": ctx.ply,
                "stage": "enrich",
                "data": {
                    "move_number": ctx.move_number,
                    "color": ctx.color,
                    "motifs": verified,
                    "features": features,
                    "comment": row.comment,
                    "completed_stages": row.completed_stages,
                },
            }
        )

    async def _emit_event(self, event: dict) -> None:
        if self._emit is None:
            return
        try:
            await self._emit(event)
        except Exception as exc:  # pragma: no cover
            logger.warning("emitter failed: %s", exc)


async def load_game(db: AsyncSession, game_id: str) -> Game | None:
    result = await db.execute(select(Game).where(Game.id == uuid.UUID(game_id)))
    return result.scalar_one_or_none()
