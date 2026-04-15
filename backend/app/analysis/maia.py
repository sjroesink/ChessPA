"""Lc0 + Maia wrapper: predicts the human-like move for a given ELO bucket.

Maia is a policy-network CNN trained on Lichess human games per rating.
We treat it as a human-behaviour predictor — NOT a strength engine.

Weight selection buckets to the nearest of {1100, 1300, 1500, 1700, 1900}
on the user's own rating, so the signal answers:
"would a player at YOUR level also fall into this move?"
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import chess
import chess.engine

from app.config import settings

def _resolve_weights_dir() -> Path:
    """Resolve settings.maia_weights_dir to an existing directory (absolute or relative-to-project)."""
    from pathlib import Path as _Path

    p = _Path(settings.maia_weights_dir)
    if p.is_absolute():
        return p
    candidates = [
        p,
        _Path.cwd() / p,
        _Path(__file__).resolve().parents[3] / p,  # project root
        _Path(__file__).resolve().parents[2] / p.name,  # backend/<name>
    ]
    for c in candidates:
        if c.exists():
            return c
    return p  # fallback (may not exist)


def _discover_ratings() -> list[int]:
    """Discover available Maia rating buckets from filenames in the weights dir."""
    import re as _re

    d = _resolve_weights_dir()
    if not d.exists():
        return [1100, 1300, 1500, 1700, 1900]  # sensible default when no weights yet
    found: list[int] = []
    for p in d.glob("maia-*.pb.gz"):
        m = _re.match(r"maia-(\d+)\.pb\.gz", p.name)
        if m:
            found.append(int(m.group(1)))
    return sorted(found) or [1100, 1300, 1500, 1700, 1900]


MAIA_RATINGS = _discover_ratings()


@dataclass
class MaiaMove:
    san: str
    uci: str
    prob: float


@dataclass
class MaiaPrediction:
    top1_san: str
    top1_uci: str
    top1_prob: float
    rating_used: int
    top_k: list[MaiaMove] = field(default_factory=list)


def pick_maia_weight(user_rating: int | None) -> tuple[Path, int]:
    """Return (weight_path, bucket_rating) nearest to user_rating; fallback = default."""
    rating = user_rating if user_rating is not None else settings.maia_default_rating
    ratings = _discover_ratings()
    bucket = min(ratings, key=lambda r: abs(r - rating))
    weight = _resolve_weights_dir() / f"maia-{bucket}.pb.gz"
    return weight, bucket


def maia_available(user_rating: int | None = None) -> bool:
    weight, _ = pick_maia_weight(user_rating)
    return weight.exists()


def open_maia_engine(rating: int | None = None) -> chess.engine.SimpleEngine:
    """Launch lc0 with the chosen Maia weight file on CUDA (or fallback backend)."""
    import shutil as _shutil

    weight, _bucket = pick_maia_weight(rating)
    if not weight.exists():
        raise FileNotFoundError(f"Maia weight missing: {weight}")
    lc0_bin = _shutil.which(settings.lc0_path) or settings.lc0_path
    # lc0 v0.32+ removed --no-smart-pruning; policy head already dominates at nodes=1
    engine = chess.engine.SimpleEngine.popen_uci(
        [
            lc0_bin,
            f"--weights={weight}",
            "--backend=cuda-fp16",
        ]
    )
    try:
        engine.configure({"Temperature": 0})
    except chess.engine.EngineError:
        # Older lc0 builds may not expose Temperature; ignore.
        pass
    return engine


_P_RE = re.compile(r"P:\s*([0-9.]+)%")


def predict_human_move(
    engine: chess.engine.SimpleEngine,
    board: chess.Board,
    rating: int | None = None,
    top_k: int = 5,
) -> MaiaPrediction:
    """Ask Maia which move a player at this ELO is likely to play.

    We run with nodes=1 so the output reflects the raw policy head. We attempt
    to parse verbose policy probabilities ("P: 42.3%") from info['string'];
    if unavailable, fall back to rank-based weights.
    """
    info_multi = engine.analyse(board, chess.engine.Limit(nodes=1), multipv=top_k)
    # engine.analyse with multipv returns a list of dicts
    infos = info_multi if isinstance(info_multi, list) else [info_multi]

    # Try to recover policy probs from string lines first
    probs_from_string: dict[str, float] = {}
    for info in infos:
        for s in info.get("string", []) or []:
            m = _P_RE.search(s)
            if m:
                # string lines contain move token too, e.g. "d2d4 ... P: 34.1%"
                tokens = s.split()
                if tokens:
                    probs_from_string[tokens[0]] = float(m.group(1)) / 100.0

    fallback = [0.6, 0.2, 0.1, 0.07, 0.03]
    moves: list[MaiaMove] = []
    for idx, info in enumerate(infos):
        pv = info.get("pv") or []
        if not pv:
            continue
        mv = pv[0]
        uci = mv.uci()
        prob = probs_from_string.get(uci)
        if prob is None:
            prob = fallback[idx] if idx < len(fallback) else 0.01
        moves.append(MaiaMove(san=board.san(mv), uci=uci, prob=prob))

    if not moves:
        raise RuntimeError("Maia returned no moves")

    _, bucket = pick_maia_weight(rating)
    return MaiaPrediction(
        top1_san=moves[0].san,
        top1_uci=moves[0].uci,
        top1_prob=moves[0].prob,
        rating_used=bucket,
        top_k=moves,
    )
