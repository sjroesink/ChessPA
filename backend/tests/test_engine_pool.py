import shutil

import chess
import pytest

from app.analysis.engine_pool import EnginePool

pytestmark = pytest.mark.skipif(shutil.which("stockfish") is None, reason="Stockfish binary not installed")


@pytest.mark.asyncio
async def test_pool_starts_and_serves_engines():
    pool = EnginePool(size=2, engine_path="stockfish", threads=1, hash_mb=16)
    try:
        await pool.start()
        async with pool.acquire() as engine:
            info = engine.analyse(chess.Board(), chess.engine.Limit(depth=4))
            assert info.get("pv")
    finally:
        await pool.stop()


@pytest.mark.asyncio
async def test_pool_enforces_max_concurrency():
    pool = EnginePool(size=1, engine_path="stockfish", threads=1, hash_mb=16)
    try:
        await pool.start()
        async with pool.acquire() as _first:
            # Second acquire should block until _first is released; we verify it
            # cannot be obtained immediately.
            import asyncio

            async def try_second():
                async with pool.acquire() as _e:
                    return True

            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(try_second(), timeout=0.2)
    finally:
        await pool.stop()
