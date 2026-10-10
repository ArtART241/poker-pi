"""Blind schedules. Levels change every N hands (not minutes, because pacing varies)."""

from __future__ import annotations

from typing import Any

from ..tables.table import Blinds

# (small blind, big blind, ante)
DEFAULT_LEVELS: list[tuple[int, int, int]] = [
    (10, 20, 0), (15, 30, 0), (25, 50, 0), (50, 100, 0), (75, 150, 0),
    (100, 200, 25), (150, 300, 25), (200, 400, 50), (300, 600, 75), (400, 800, 100),
    (600, 1200, 150), (800, 1600, 200), (1000, 2000, 250), (1500, 3000, 400), (2000, 4000, 500),
]

DEFAULT_CONFIG: dict[str, Any] = {
    "starting_stack": 1500,
    "hands_per_level": 10,
    "levels": DEFAULT_LEVELS,
    "pacing": {"action": 2.0, "street": 1.5, "hand_end": 4.0},
    "max_players": 9,
}


def full_config(overrides: dict[str, Any] | None) -> dict[str, Any]:
    cfg = {**DEFAULT_CONFIG, **(overrides or {})}
    cfg["pacing"] = {**DEFAULT_CONFIG["pacing"], **(overrides or {}).get("pacing", {})}
    cfg["levels"] = [tuple(level) for level in cfg["levels"]]
    return cfg


def blinds_for(levels: list[tuple[int, int, int]], hands_per_level: int, hand_no: int) -> Blinds:
    """hand_no counts from 0."""
    idx = hand_no // hands_per_level
    if idx < len(levels):
        sb, bb, ante = levels[idx]
    else:  # past the schedule: keep doubling the last level
        factor = 2 ** (idx - len(levels) + 1)
        sb, bb, ante = (x * factor for x in levels[-1])
    return Blinds(sb, bb, ante, idx + 1, hands_per_level - hand_no % hands_per_level)
