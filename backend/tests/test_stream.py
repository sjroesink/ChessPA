import asyncio
import shutil

import chess
import pytest

from app.analysis.engine_pool import EnginePool
from app.analysis.stream import run_stage

pytestmark = pytest.mark.skipif(shutil.which("stockfish") is None, reason="Stockfish binary not installed")


@pytest.mark.asyncio
async def test_run_stage_shallow_produces_pv():
    pool = EnginePool(size=1, engine_path="stockfish", threads=1, hash_mb=16)
    try:
        await pool.start()
        async with pool.acquire() as engine:
            result = await run_stage(engine, chess.Board(), "shallow")
        assert result.stage == "shallow"
        assert result.depth_reached >= 1
        assert result.multipv and result.multipv[0].san
    finally:
        await pool.stop()


@pytest.mark.asyncio
async def test_run_stage_honours_cancel_event():
    pool = EnginePool(size=1, engine_path="stockfish", threads=1, hash_mb=16)
    try:
        await pool.start()
        async with pool.acquire() as engine:
            cancel = asyncio.Event()
            cancel.set()  # pre-cancel so run_stage stops near-immediately
            result = await run_stage(engine, chess.Board(), "deep", cancel_event=cancel)
        assert result.stopped_early is True
    finally:
        await pool.stop()


@pytest.mark.asyncio
async def test_run_stage_enrich_is_noop():
    pool = EnginePool(size=1, engine_path="stockfish", threads=1, hash_mb=16)
    try:
        await pool.start()
        async with pool.acquire() as engine:
            result = await run_stage(engine, chess.Board(), "enrich")
        assert result.stage == "enrich"
        assert result.multipv == []
        assert result.depth_reached == 0
    finally:
        await pool.stop()
