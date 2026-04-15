from app.analysis.stages import (
    ALL_STAGES,
    load_stage_spec,
    mark_stage_complete,
    missing_stages,
)


def test_all_stages_listed_in_order():
    assert ALL_STAGES == ("shallow", "standard", "deep", "enrich")


def test_load_stage_spec_returns_non_zero_depth_for_engine_stages():
    for name in ("shallow", "standard", "deep"):
        spec = load_stage_spec(name)
        assert spec.depth_target > 0
        assert spec.multipv >= 1


def test_enrich_has_standard_prerequisite():
    spec = load_stage_spec("enrich")
    assert "standard" in spec.requires


def test_missing_stages_none_completed():
    assert missing_stages(None) == list(ALL_STAGES)


def test_missing_stages_shallow_done():
    assert missing_stages(["shallow"]) == ["standard", "deep", "enrich"]


def test_missing_stages_all_done_is_empty():
    assert missing_stages(list(ALL_STAGES)) == []


def test_mark_stage_complete_idempotent():
    assert mark_stage_complete(None, "shallow") == ["shallow"]
    assert mark_stage_complete(["shallow"], "shallow") == ["shallow"]
    assert mark_stage_complete(["shallow"], "standard") == ["shallow", "standard"]
