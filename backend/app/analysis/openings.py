"""Opening classifier using the Lichess CC0 opening book (ECO + name)."""

import csv
from functools import lru_cache
from pathlib import Path

from app.config import settings


@lru_cache(maxsize=1)
def _load_book() -> dict[str, tuple[str, str]]:
    """Return {normalized_san_sequence: (eco, name)} where keys are space-joined SAN without move numbers."""
    book: dict[str, tuple[str, str]] = {}
    path = Path(settings.opening_book_path)
    if not path.is_absolute():
        # allow relative path from project root or backend/
        candidates = [
            path,
            Path("backend") / path,
            Path(__file__).resolve().parents[3] / path,
        ]
        for candidate in candidates:
            if candidate.exists():
                path = candidate
                break
    if not path.exists():
        return book
    with open(path, encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if len(row) < 3 or row[0].lower() == "eco":
                continue
            eco, name, pgn = row[0], row[1], row[2]
            tokens = [t for t in pgn.split() if not t.endswith(".")]
            key = " ".join(tokens)
            book[key] = (eco, name)
    return book


def classify_opening(san_moves: list[str]) -> tuple[str | None, str | None]:
    """Longest-prefix match against Lichess book. Returns (eco, name) or (None, None)."""
    book = _load_book()
    if not book:
        return (None, None)
    for n in range(min(len(san_moves), 30), 0, -1):
        key = " ".join(san_moves[:n])
        if key in book:
            return book[key]
    return (None, None)
