from app.chess_services.pgn_parser import parse_pgn, compute_content_hash, determine_result


SAMPLE_PGN = """[Event "Live Chess"]
[Site "Chess.com"]
[Date "2026.04.10"]
[Round "-"]
[White "player1"]
[Black "player2"]
[Result "1-0"]
[WhiteElo "1700"]
[BlackElo "1650"]
[TimeControl "600"]
[ECO "B90"]
[Opening "Sicilian Defense: Najdorf Variation"]

1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 1-0"""


SAMPLE_PGN_NO_HEADERS = """1. e4 e5 *"""


def test_parse_pgn_full():
    result = parse_pgn(SAMPLE_PGN)
    assert result["white_username"] == "player1"
    assert result["black_username"] == "player2"
    assert result["result_raw"] == "1-0"
    assert result["white_elo"] == 1700
    assert result["black_elo"] == 1650
    assert result["time_control"] == "600"
    assert result["opening_eco"] == "B90"
    assert result["opening_name"] == "Sicilian Defense: Najdorf Variation"
    assert result["move_count"] == 6
    assert result["played_at"] is not None


def test_parse_pgn_minimal():
    result = parse_pgn(SAMPLE_PGN_NO_HEADERS)
    assert result["white_username"] == "?"
    assert result["move_count"] == 2


def test_compute_content_hash():
    hash1 = compute_content_hash("1. e4 e5 *", "2026-04-10", "p1", "p2")
    hash2 = compute_content_hash("1. e4 e5 *", "2026-04-10", "p1", "p2")
    hash3 = compute_content_hash("1. d4 d5 *", "2026-04-10", "p1", "p2")
    assert hash1 == hash2
    assert hash1 != hash3
    assert len(hash1) == 64


def test_determine_result():
    assert determine_result("1-0", True) == "win"
    assert determine_result("1-0", False) == "loss"
    assert determine_result("0-1", True) == "loss"
    assert determine_result("0-1", False) == "win"
    assert determine_result("1/2-1/2", True) == "draw"
