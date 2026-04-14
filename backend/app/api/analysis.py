import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
        select(Game).where(Game.id == uuid.UUID(game_id), Game.user_id == user.id)
    )
    game = result.scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")

    moves_result = await db.execute(
        select(MoveAnalysis).where(MoveAnalysis.game_id == game.id)
        # color DESC so "white" comes before "black" per move_number
        .order_by(MoveAnalysis.move_number, MoveAnalysis.color.desc())
    )
    moves = moves_result.scalars().all()

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
                "fen": m.fen,
                "comment": m.comment,
                "win_percent_before": m.win_percent_before,
                "win_percent_after": m.win_percent_after,
                "accuracy_percent": m.accuracy_percent,
                "is_critical_moment": m.is_critical_moment,
                "maia": {
                    "top1_san": m.maia_top1_san,
                    "top1_prob": m.maia_top1_prob,
                    "match_played": m.maia_match_played,
                    "rating_used": m.maia_rating_used,
                },
                "details": m.details_json or {},
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
            "accuracy_white": summary.accuracy_white,
            "accuracy_black": summary.accuracy_black,
            "opening_eco": summary.opening_eco,
            "opening_name": summary.opening_name,
            "phase_acpl": summary.phase_acpl,
            "motif_counts": summary.motif_counts,
        } if summary else None,
    }
