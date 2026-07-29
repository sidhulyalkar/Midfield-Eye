from __future__ import annotations

from typing import Any

from .catalog import PlayerCatalog, PlayerStudy, load_player_catalog
from .scenarios import SCENARIOS, ShowcaseScenario, build_scenario_frames, list_scenarios


def build_showcase_bundle(*args: Any, **kwargs: Any):
    """Lazy import avoids a visualization/export initialization cycle."""
    from .export import build_showcase_bundle as _build

    return _build(*args, **kwargs)


__all__ = [
    "PlayerCatalog",
    "PlayerStudy",
    "SCENARIOS",
    "ShowcaseScenario",
    "build_scenario_frames",
    "build_showcase_bundle",
    "list_scenarios",
    "load_player_catalog",
]
