"""Process-global pool of long-lived Stockfish engines.

Opening a Stockfish subprocess + warming its hash table costs ~100-300 ms.
Doing it on every WebSocket connect or Celery task is wasteful. The pool is
created once at FastAPI startup (lifespan) and shared across all sessions.

One engine is owned by at most one coroutine at a time — python-chess
`engine.analyse` / `engine.analysis` on `SimpleEngine` is NOT thread-safe, and
neither is Stockfish on a shared subprocess. `async with pool.acquire()` hands
out a single engine and returns it when the `with` block exits.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

import chess.engine

from app.config import settings

logger = logging.getLogger(__name__)


class EnginePool:
    def __init__(self, size: int, engine_path: str, threads: int, hash_mb: int):
        self._size = max(1, size)
        self._engine_path = engine_path
        self._threads = threads
        self._hash_mb = hash_mb
        self._queue: asyncio.Queue[chess.engine.SimpleEngine] = asyncio.Queue(maxsize=self._size)
        self._all: list[chess.engine.SimpleEngine] = []
        self._started = False
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        async with self._lock:
            if self._started:
                return
            for _ in range(self._size):
                engine = await asyncio.to_thread(self._open_engine)
                self._all.append(engine)
                await self._queue.put(engine)
            self._started = True
            logger.info("EnginePool started with %d engines", self._size)

    def _open_engine(self) -> chess.engine.SimpleEngine:
        engine = chess.engine.SimpleEngine.popen_uci(self._engine_path)
        engine.configure({"Threads": self._threads, "Hash": self._hash_mb})
        return engine

    async def stop(self) -> None:
        async with self._lock:
            if not self._started:
                return
            for engine in self._all:
                try:
                    await asyncio.to_thread(engine.quit)
                except Exception:
                    pass
            self._all.clear()
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            self._started = False
            logger.info("EnginePool stopped")

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[chess.engine.SimpleEngine]:
        """Borrow an engine. The caller has exclusive use until the block exits."""
        if not self._started:
            await self.start()
        engine = await self._queue.get()
        try:
            yield engine
        finally:
            await self._queue.put(engine)


_pool: EnginePool | None = None


def configure_pool(pool: EnginePool | None) -> None:
    global _pool
    _pool = pool


def get_pool() -> EnginePool:
    if _pool is None:
        raise RuntimeError("EnginePool not initialised. Did the FastAPI lifespan run?")
    return _pool


def build_default_pool() -> EnginePool:
    return EnginePool(
        size=settings.analysis_engine_pool_size,
        engine_path=settings.stockfish_path,
        threads=settings.stockfish_threads,
        hash_mb=settings.stockfish_hash_mb,
    )
