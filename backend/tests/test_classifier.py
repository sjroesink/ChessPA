from app.analysis.classifier import classify_move

def test_best_move():
    assert classify_move(0) == "best"
    assert classify_move(5) == "best"
    assert classify_move(10) == "best"

def test_good_move():
    assert classify_move(11) == "good"
    assert classify_move(25) == "good"

def test_inaccuracy():
    assert classify_move(26) == "inaccuracy"
    assert classify_move(50) == "inaccuracy"

def test_mistake():
    assert classify_move(51) == "mistake"
    assert classify_move(100) == "mistake"

def test_blunder():
    assert classify_move(101) == "blunder"
    assert classify_move(500) == "blunder"
