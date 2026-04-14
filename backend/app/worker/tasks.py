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
def analyze_game(game_id: str):
    """Analyze a single game with Stockfish and persist results."""
    return asyncio.run(_analyze_game_async(game_id))


async def _analyze_game_async(game_id: str):
    import io
    import uuid

    import chess
    import chess.pgn

    from app.analysis.maia import maia_available, open_maia_engine
    from app.analysis.motifs import detect_geometric_motifs, verify_motifs
    from app.analysis.positional import extract_features

    engine_instance = None
    maia_engine = None
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

            maia_rating = game.user_elo
            try:
                engine_instance = open_engine()
                if settings.enable_maia and maia_available(maia_rating):
                    try:
                        maia_engine = open_maia_engine(rating=maia_rating)
                    except Exception as e:
                        print(f"Maia init failed; continuing without: {e}")
                        maia_engine = None
                move_results = analyze_game_moves(
                    engine_instance,
                    game.pgn,
                    maia_engine=maia_engine,
                    maia_rating=maia_rating,
                )

                if settings.enable_motifs:
                    for mr in move_results:
                        board = chess.Board(mr["fen"])
                        geo = detect_geometric_motifs(board)
                        verified = verify_motifs(engine_instance, board, geo) if geo else []
                        mr["motifs"] = verified
                        mr["features"] = extract_features(board)
                else:
                    for mr in move_results:
                        mr["motifs"] = []
                        mr["features"] = extract_features(chess.Board(mr["fen"]))
            except Exception as e:
                game.analysis_status = "failed"
                await db.commit()
                return {"error": str(e)}

            for mr in move_results:
                details = {
                    "multipv": mr.get("multipv", []),
                    "motifs": mr.get("motifs", []),
                    "features": mr.get("features", {}),
                }
                ma = MoveAnalysis(
                    game_id=game.id,
                    move_number=mr["move_number"],
                    color=mr["color"],
                    move_san=mr["move_san"],
                    eval_before=mr["eval_before"],
                    eval_after=mr["eval_after"],
                    best_move_san=mr["best_move_san"],
                    classification=mr["classification"],
                    fen=mr.get("fen"),
                    win_percent_before=mr.get("win_percent_before"),
                    win_percent_after=mr.get("win_percent_after"),
                    accuracy_percent=mr.get("accuracy_percent"),
                    is_critical_moment=mr.get("is_critical_moment"),
                    maia_top1_san=mr.get("maia_top1_san"),
                    maia_top1_prob=mr.get("maia_top1_prob"),
                    maia_match_played=mr.get("maia_match_played"),
                    maia_rating_used=mr.get("maia_rating_used"),
                    details_json=details,
                )
                db.add(ma)

            # Collect opening SAN moves (first 20 plies) for ECO classification
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

            summary_data = compute_game_summary(move_results, opening_moves_san=opening_sans)

            game_summary = GameSummary(
                game_id=game.id,
                blunders=summary_data["blunders"],
                mistakes=summary_data["mistakes"],
                inaccuracies=summary_data["inaccuracies"],
                avg_eval_loss=summary_data["avg_eval_loss"],
                phase_scores=summary_data["phase_scores"],
                time_trouble=summary_data["time_trouble"],
                accuracy_white=summary_data.get("accuracy_white"),
                accuracy_black=summary_data.get("accuracy_black"),
                opening_eco=summary_data.get("opening_eco"),
                opening_name=summary_data.get("opening_name"),
                phase_acpl=summary_data.get("phase_acpl"),
                motif_counts=summary_data.get("motif_counts"),
            )
            db.add(game_summary)
            game.analysis_status = "done"
            await db.commit()

            try:
                generate_move_commentary_task.delay(str(game.id))
            except Exception:
                pass

            return {"status": "done", "moves_analyzed": len(move_results), "blunders": summary_data["blunders"]}
    finally:
        if engine_instance:
            engine_instance.quit()
        await engine_db.dispose()


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
