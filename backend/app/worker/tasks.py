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
from app.analysis.analyzer import analyze_game_moves
from app.analysis.stockfish import open_engine
from app.analysis.summary import compute_game_summary


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

            game.analysis_status = "analyzing"
            await db.commit()

            try:
                engine_instance = open_engine()
                move_results = analyze_game_moves(engine_instance, game.pgn)
            except Exception as e:
                game.analysis_status = "failed"
                await db.commit()
                return {"error": str(e)}

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

            return {"status": "done", "moves_analyzed": len(move_results), "blunders": summary_data["blunders"]}
    finally:
        if engine_instance:
            engine_instance.quit()
        await engine_db.dispose()
