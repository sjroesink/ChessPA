"""Streaming stage runner.

Wraps python-chess's `engine.analysis()` (an async iterator of `info` events)
so a caller can:
  - consume intermediate depths as they arrive (for live WebSocket updates),
  - stop the engine early via UCI `stop` when preempted by a higher-priority
    work unit,
  - reason about the final result in a uniform shape regardless of stage.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

import chess
import chess.engine

from app.analysis.stages import StageName, load_stage_spec


@dataclass
class PVLineDict:
    rank: int
    san: str
    uci: str
    eval_cp: float
    pv_san: list[str]

    def as_dict(self) -> dict:
        return {
            "rank": self.rank,
            "san": self.san,
            "uci": self.uci,
            "eval_cp": self.eval_cp,
            "pv_san": self.pv_san,
        }


@dataclass
class StageRunResult:
    stage: StageName
    depth_reached: int
    multipv: list[PVLineDict] = field(default_factory=list)
    stopped_early: bool = False
    elapsed_ms: int = 0

    def best(self) -> PVLineDict | None:
        return self.multipv[0] if self.multipv else None

    def as_dict(self) -> dict:
        return {
            "stage": self.stage,
            "depth_reached": self.depth_reached,
            "multipv": [pv.as_dict() for pv in self.multipv],
            "stopped_early": self.stopped_early,
            "elapsed_ms": self.elapsed_ms,
        }


def _score_to_cp(score: chess.engine.PovScore, turn: chess.Color) -> float:
    relative = score.relative
    if relative.is_mate():
        mate_in = relative.mate() or 0
        return 10000 if mate_in > 0 else -10000
    return float(relative.score(mate_score=10000))


def _collect_multipv(
    infos: list[dict] | None,
    board: chess.Board,
) -> list[PVLineDict]:
    """Build PVLineDict list from a MultiPV analysis snapshot."""
    if not infos:
        return []
    out: list[PVLineDict] = []
    for info in infos:
        pv_moves = info.get("pv") or []
        if not pv_moves:
            continue
        best = pv_moves[0]
        clone = board.copy(stack=False)
        pv_sans: list[str] = []
        for mv in pv_moves[:8]:
            try:
                pv_sans.append(clone.san(mv))
                clone.push(mv)
            except (AssertionError, ValueError):
                break
        score = info.get("score")
        eval_cp = _score_to_cp(score, board.turn) if score is not None else 0.0
        out.append(
            PVLineDict(
                rank=info.get("multipv", len(out) + 1),
                san=board.san(best),
                uci=best.uci(),
                eval_cp=eval_cp,
                pv_san=pv_sans,
            )
        )
    out.sort(key=lambda pv: pv.rank)
    return out


async def run_stage(
    engine: chess.engine.SimpleEngine,
    board: chess.Board,
    stage: StageName,
    cancel_event: asyncio.Event | None = None,
    on_progress=None,
) -> StageRunResult:
    """Analyse `board` using `stage`'s depth/time/multipv settings.

    Emits intermediate snapshots via `on_progress(result)` at each depth
    increment so callers can surface live info (e.g. WebSocket updates).

    `cancel_event` (if set) triggers an early UCI stop and returns the best
    result so far with `stopped_early=True`.

    For stages with depth_target==0 (like "enrich") this returns an empty
    result immediately — enrichment is handled outside this streaming path.
    """
    spec = load_stage_spec(stage)
    result = StageRunResult(stage=stage, depth_reached=0)

    if spec.depth_target <= 0:
        return result

    limit = chess.engine.Limit(
        depth=spec.depth_target,
        time=spec.time_budget_ms / 1000.0 if spec.time_budget_ms else None,
    )

    started = time.perf_counter()

    def _elapsed_ms() -> int:
        return int((time.perf_counter() - started) * 1000)

    analysis = await asyncio.to_thread(
        engine.analysis, board, limit, multipv=spec.multipv
    )

    try:
        while True:
            if cancel_event is not None and cancel_event.is_set():
                result.stopped_early = True
                analysis.stop()
                break
            try:
                info = await asyncio.to_thread(analysis.get)
            except chess.engine.AnalysisComplete:
                break
            # AnalysisResult yields dicts for single-PV or lists for multipv via .multipv snapshots
            snapshot = analysis.multipv  # list of latest info dicts per rank
            lines = _collect_multipv(list(snapshot), board)
            if lines:
                result.multipv = lines
            depth = info.get("depth")
            if depth is not None and depth > result.depth_reached:
                result.depth_reached = depth
                result.elapsed_ms = _elapsed_ms()
                if on_progress is not None:
                    try:
                        on_progress(result)
                    except Exception:
                        pass
            if spec.time_budget_ms and _elapsed_ms() >= spec.time_budget_ms:
                analysis.stop()
                result.stopped_early = True
                break
            if info.get("depth") is not None and info["depth"] >= spec.depth_target:
                # target depth reached for the last-indexed PV; wait for engine to finish current iter
                pass
    finally:
        try:
            analysis.stop()
        except Exception:
            pass

    # Final snapshot after engine finishes / stops.
    final = _collect_multipv(list(analysis.multipv), board)
    if final:
        result.multipv = final
    result.elapsed_ms = _elapsed_ms()
    return result
