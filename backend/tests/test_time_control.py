from app.chess_services.time_control import classify_time_control


def test_bullet():
    assert classify_time_control("60") == "bullet"
    assert classify_time_control("60+1") == "bullet"
    assert classify_time_control("120") == "bullet"
    assert classify_time_control("120+1") == "bullet"


def test_blitz():
    assert classify_time_control("180") == "blitz"
    assert classify_time_control("180+2") == "blitz"
    assert classify_time_control("300") == "blitz"
    assert classify_time_control("300+0") == "blitz"
    assert classify_time_control("300+3") == "blitz"


def test_rapid():
    assert classify_time_control("600") == "rapid"
    assert classify_time_control("600+0") == "rapid"
    assert classify_time_control("900") == "rapid"
    assert classify_time_control("900+10") == "rapid"
    assert classify_time_control("1500") == "rapid"
    assert classify_time_control("1800") == "rapid"


def test_classical():
    assert classify_time_control("1800+30") == "classical"
    assert classify_time_control("2700") == "classical"
    assert classify_time_control("3600") == "classical"
    assert classify_time_control("5400") == "classical"


def test_unknown():
    assert classify_time_control(None) == "unknown"
    assert classify_time_control("") == "unknown"
    assert classify_time_control("-") == "unknown"
