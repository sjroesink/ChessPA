"""Per-ply analysis stages for progressive, priority-driven evaluation.

Each stage is independently completable and persisted on a MoveAnalysis row via
the `completed_stages` JSONB column. The pipeline schedules only the stages
that are still missing for a given ply.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

StageName = Literal["shallow", "standard", "deep", "enrich"]


@dataclass(frozen=True)
class StageSpec:
    name: StageName
    depth_target: int           # engine searches to at least this depth
    time_budget_ms: int         # ...or until this many ms have passed
    multipv: int                # number of principal variations
    requires: tuple[StageName, ...]  # upstream stages (currently empty for all — stages are independent)


# Concrete stage definitions. Depth/time values are overridable via settings.
STAGES: dict[StageName, StageSpec] = {
    "shallow": StageSpec(name="shallow", depth_target=10, time_budget_ms=200, multipv=1, requires=()),
    "standard": StageSpec(name="standard", depth_target=18, time_budget_ms=1500, multipv=3, requires=()),
    "deep": StageSpec(name="deep", depth_target=24, time_budget_ms=5000, multipv=3, requires=()),
    "enrich": StageSpec(name="enrich", depth_target=0, time_budget_ms=0, multipv=0, requires=("standard",)),
}

ALL_STAGES: tuple[StageName, ...] = ("shallow", "standard", "deep", "enrich")


def load_stage_spec(name: StageName) -> StageSpec:
    """Return the stage spec, allowing runtime overrides from app settings."""
    from app.config import settings

    base = STAGES[name]
    overrides = {
        "shallow": (
            getattr(settings, "analysis_shallow_depth", base.depth_target),
            getattr(settings, "analysis_shallow_time_budget_ms", base.time_budget_ms),
        ),
        "standard": (
            getattr(settings, "analysis_standard_target_depth", base.depth_target),
            getattr(settings, "analysis_standard_time_budget_ms", base.time_budget_ms),
        ),
        "deep": (
            getattr(settings, "analysis_deep_target_depth", base.depth_target),
            getattr(settings, "analysis_deep_time_budget_ms", base.time_budget_ms),
        ),
        "enrich": (0, 0),
    }
    depth, time_ms = overrides.get(name, (base.depth_target, base.time_budget_ms))
    return StageSpec(
        name=base.name,
        depth_target=depth,
        time_budget_ms=time_ms,
        multipv=base.multipv,
        requires=base.requires,
    )


def missing_stages(completed: list[str] | None, desired: tuple[StageName, ...] = ALL_STAGES) -> list[StageName]:
    """Return the stages from `desired` that are not yet in `completed`."""
    done = set(completed or [])
    return [s for s in desired if s not in done]


def mark_stage_complete(completed: list[str] | None, stage: StageName) -> list[str]:
    """Idempotently add a stage to the completed list while preserving order."""
    current = list(completed or [])
    if stage not in current:
        current.append(stage)
    return current
