import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.worker.celery_app import celery_app
from app.models.connected_account import ConnectedAccount
from app.chess_services.chesscom import fetch_recent_games as fetch_chesscom_games
from app.chess_services.lichess_client import fetch_recent_games as fetch_lichess_games
from app.chess_services.import_service import import_chesscom_game, import_lichess_game
from app.models.game import Game
from app.models.move_analysis import MoveAnalysis
from app.models.game_summary import GameSummary
from app.models.user import User
from app.coaching.service import generate_coaching_insights
from app.analysis.analyzer import analyze_game_moves
from app.analysis.stockfish import open_engine
from app.analysis.summary import compute_game_summary
from app.analysis.commentary import generate_move_commentary


def _get_session_factory():
    engine = create_async_engine(settings.database_url)
    return engine, async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _sync_account(account, user_id, db):
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
    return asyncio.run(_sync_all_accounts_async())


async def _sync_all_accounts_async():
    engine, factory = _get_session_factory()
    total_imported = 0
    accounts_count = 0

    async with factory() as db:
        result = await db.execute(
            select(ConnectedAccount).where(ConnectedAccount.auto_sync == True)
        )
        accounts = result.scalars().all()
        accounts_count = len(accounts)

        for account in accounts:
            try:
                count = await _sync_account(account, account.user_id, db)
                total_imported += count
            except Exception as e:
                print(f"Sync error for {account.platform}/{account.platform_username}: {e}")

    await engine.dispose()
    return {"imported": total_imported, "accounts_processed": accounts_count}


@celery_app.task(name="app.worker.tasks.analyze_game")
def analyze_game(game_id: str, stages: list[str] | None = None):
    """Progressive shallow-scan of a game (fast background pass).

    Default: run only the "shallow" stage so the games-list + dashboard pick
    up eval/accuracy within seconds. Deeper stages are computed on-demand by
    the WebSocket path when the user opens the game.
    """
    return asyncio.run(_analyze_game_async(game_id, stages=stages or ["shallow"]))


async def _analyze_game_async(game_id: str, stages: list[str]):
    import io
    import uuid

    import chess
    import chess.pgn

    from app.analysis.engine_pool import EnginePool
    from app.analysis.pipeline import AnalysisSession
    from app.analysis.stages import StageName  # noqa: F401

    engine_db, factory = _get_session_factory()
    pool = EnginePool(
        size=1,
        engine_path=settings.stockfish_path,
        threads=settings.stockfish_threads,
        hash_mb=settings.stockfish_hash_mb,
    )

    try:
        await pool.start()
        async with factory() as db:
            result = await db.execute(
                select(Game).where(Game.id == uuid.UUID(game_id))
            )
            game = result.scalar_one_or_none()
            if game is None:
                return {"error": "Game not found"}

            # Respect WebSocket ownership: if a live session holds focus, skip.
            import redis as _redis

            r = _redis.from_url(settings.redis_url, decode_responses=True)
            lock_key = f"analysis:focus:{game_id}"
            if r.exists(lock_key):
                return {"status": "skipped_live_session_active"}

            game.analysis_status = "analyzing"
            await db.commit()

            def _logger(ply: int, total: int, move_number: int, color: str, san: str) -> None:
                label = f"{move_number}.{'' if color == 'white' else '..'}{san}"
                print(f"[analyze:{stages[0]}] ply {ply + 1}/{total} {color} {label}")

            try:
                session = AnalysisSession(db=db, game=game, pool=pool, emitter=None)
                await session.load()
                session.set_desired_stages(stages)
                await session.run()
            except Exception as e:  # pragma: no cover
                game.analysis_status = "failed"
                await db.commit()
                return {"error": str(e)}

            # Re-fetch persisted rows for summary + stage rollup
            rows_result = await db.execute(
                select(MoveAnalysis).where(MoveAnalysis.game_id == game.id)
                .order_by(MoveAnalysis.move_number, MoveAnalysis.color.desc())
            )
            rows = rows_result.scalars().all()

            move_dicts = [
                {
                    "move_number": r.move_number,
                    "color": r.color,
                    "classification": r.classification,
                    "centipawn_loss": max(0.0, (r.eval_before or 0) - (r.eval_after or 0)),
                    "accuracy_percent": r.accuracy_percent,
                    "move_number_int": r.move_number,
                    "total_moves": len(rows) // 2,
                    "features": (r.details_json or {}).get("features", {}),
                    "motifs": (r.details_json or {}).get("motifs", []),
                }
                for r in rows
            ]

            opening_sans: list[str] = []
            try:
                pgn_game = chess.pgn.read_game(io.StringIO(game.pgn))
                if pgn_game is not None:
                    b = pgn_game.board()
                    for mv in list(pgn_game.mainline_moves())[:20]:
                        opening_sans.append(b.san(mv))
                        b.push(mv)
            except Exception:
                opening_sans = []

            summary_data = compute_game_summary(move_dicts, opening_moves_san=opening_sans)

            # Upsert GameSummary
            existing = await db.execute(
                select(GameSummary).where(GameSummary.game_id == game.id)
            )
            summary_row = existing.scalar_one_or_none()
            if summary_row is None:
                summary_row = GameSummary(game_id=game.id)
                db.add(summary_row)
            summary_row.blunders = summary_data["blunders"]
            summary_row.mistakes = summary_data["mistakes"]
            summary_row.inaccuracies = summary_data["inaccuracies"]
            summary_row.avg_eval_loss = summary_data["avg_eval_loss"]
            summary_row.phase_scores = summary_data["phase_scores"]
            summary_row.time_trouble = summary_data["time_trouble"]
            summary_row.accuracy_white = summary_data.get("accuracy_white")
            summary_row.accuracy_black = summary_data.get("accuracy_black")
            summary_row.opening_eco = summary_data.get("opening_eco")
            summary_row.opening_name = summary_data.get("opening_name")
            summary_row.phase_acpl = summary_data.get("phase_acpl")
            summary_row.motif_counts = summary_data.get("motif_counts")

            # Game-level stage rollup: highest stage present on every row wins.
            if rows:
                per_row = [set(r.completed_stages or []) for r in rows]
                common = set.intersection(*per_row) if per_row else set()
                for stage in ("deep", "standard", "shallow"):
                    if stage in common:
                        game.analysis_stage = stage
                        break
                else:
                    game.analysis_stage = None
            game.analysis_status = "done" if game.analysis_stage else "pending"
            await db.commit()

            return {
                "status": "done",
                "stage": stages[0],
                "moves_analyzed": len(rows),
                "game_stage": game.analysis_stage,
            }
    finally:
        await pool.stop()
        await engine_db.dispose()


@celery_app.task(name="app.worker.tasks.deep_scan_all")
def deep_scan_all(user_id: str):
    """Run deep + enrich stages for every analysed game belonging to `user_id`.

    Yields priority to any live WebSocket session: before starting work on a
    game we check `analysis:focus:{game_id}`; if set, skip and retry later.
    """
    return asyncio.run(_deep_scan_all_async(user_id))


async def _deep_scan_all_async(user_id: str):
    import uuid as _uuid

    import redis as _redis

    engine_db, factory = _get_session_factory()
    r = _redis.from_url(settings.redis_url, decode_responses=True)
    total_games = 0
    completed_games = 0
    skipped_games = 0

    async with factory() as db:
        result = await db.execute(
            select(Game).where(Game.user_id == _uuid.UUID(user_id))
        )
        games = result.scalars().all()
    total_games = len(games)

    for g in games:
        gid = str(g.id)
        if r.exists(f"analysis:focus:{gid}"):
            skipped_games += 1
            continue
        try:
            await _analyze_game_async(gid, stages=["standard", "deep", "enrich"])
            completed_games += 1
        except Exception as exc:  # pragma: no cover
            print(f"deep_scan_all error on {gid}: {exc}")

    await engine_db.dispose()
    return {
        "user_id": user_id,
        "total": total_games,
        "completed": completed_games,
        "skipped": skipped_games,
    }


@celery_app.task(name="app.worker.tasks.generate_all_coaching")
def generate_all_coaching():
    """Generate coaching insights for all users with enough analyzed games."""
    return asyncio.run(_generate_all_coaching_async())


async def _generate_all_coaching_async():
    engine, factory = _get_session_factory()
    total_generated = 0

    async with factory() as db:
        result = await db.execute(select(User))
        users = result.scalars().all()

        for user in users:
            try:
                insights = await generate_coaching_insights(db, user.id)
                total_generated += len(insights)
            except Exception as e:
                print(f"Coaching error for user {user.username}: {e}")

    await engine.dispose()
    return {"users_processed": len(users), "insights_generated": total_generated}


@celery_app.task(name="app.worker.tasks.generate_move_commentary_task")
def generate_move_commentary_task(game_id: str):
    """Generate LLM commentary for significant move errors in a game."""
    return asyncio.run(_generate_move_commentary_async(game_id))


async def _generate_move_commentary_async(game_id: str):
    import uuid
    engine_db, factory = _get_session_factory()

    async with factory() as db:
        # Load game for user_color
        game_result = await db.execute(
            select(Game).where(Game.id == uuid.UUID(game_id))
        )
        game = game_result.scalar_one_or_none()
        if game is None:
            await engine_db.dispose()
            return {"error": "Game not found"}

        # Load move analyses for this game
        result = await db.execute(
            select(MoveAnalysis).where(MoveAnalysis.game_id == uuid.UUID(game_id))
        )
        analyses = result.scalars().all()

        if not analyses:
            await engine_db.dispose()
            return {"error": "No move analyses found"}

        # Build rich move dicts for CCC commentary
        move_dicts = []
        for ma in analyses:
            if not ma.fen:
                continue  # skip moves without FEN (pre-migration)
            details = ma.details_json or {}
            move_dicts.append(
                {
                    "move_number": ma.move_number,
                    "color": ma.color,
                    "move_san": ma.move_san,
                    "best_move_san": ma.best_move_san,
                    "classification": ma.classification,
                    "eval_before": ma.eval_before,
                    "eval_after": ma.eval_after,
                    "centipawn_loss": abs(ma.eval_before - ma.eval_after),
                    "win_percent_before": ma.win_percent_before,
                    "win_percent_after": ma.win_percent_after,
                    "accuracy_percent": ma.accuracy_percent,
                    "is_critical_moment": ma.is_critical_moment,
                    "maia_top1_san": ma.maia_top1_san,
                    "maia_top1_prob": ma.maia_top1_prob,
                    "maia_match_played": ma.maia_match_played,
                    "maia_rating_used": ma.maia_rating_used,
                    "fen": ma.fen,
                    "multipv": details.get("multipv", []),
                    "motifs": details.get("motifs", []),
                    "features": details.get("features", {}),
                }
            )

        comments = await generate_move_commentary(move_dicts, game.user_color)

        # Update move analyses with comments
        updated = 0
        for ma in analyses:
            key = (ma.move_number, ma.color)
            if key in comments:
                ma.comment = comments[key]
                updated += 1

        await db.commit()

    await engine_db.dispose()
    return {"game_id": game_id, "comments_added": updated}
