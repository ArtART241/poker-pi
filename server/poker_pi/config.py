"""Settings, read from environment variables (all optional)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _env_float(name: str, default: float) -> float:
    return float(os.environ.get(name, default))


@dataclass
class Settings:
    db_path: str = field(default_factory=lambda: os.environ.get(
        "POKER_DB", str(_REPO_ROOT / "data" / "poker.db")))
    static_dir: str = field(default_factory=lambda: os.environ.get(
        "POKER_STATIC_DIR", str(_REPO_ROOT / "web" / "dist")))
    # seconds a bot has for one decision
    decision_timeout: float = field(default_factory=lambda: _env_float("POKER_DECISION_TIMEOUT", 15))
    # a bot that is sitting out gets this long to answer before it is auto-folded again
    sitout_grace: float = field(default_factory=lambda: _env_float("POKER_SITOUT_GRACE", 3))
    # consecutive timeouts until a bot is sat out
    max_timeouts: int = field(default_factory=lambda: int(os.environ.get("POKER_MAX_TIMEOUTS", 3)))
    # a bot that has not polled /turn for this long counts as disconnected
    disconnect_after: float = field(default_factory=lambda: _env_float("POKER_DISCONNECT_AFTER", 60))
    # default card style on the website: "drawn" or "artwork" (viewers can switch in the settings)
    card_deck: str = field(default_factory=lambda: os.environ.get("POKER_CARD_DECK", "drawn"))
    max_wait: int = 30
    scheduler_interval: float = 1.0
    # requests per second a single bot may send (long-polls included)
    rate_limit: int = field(default_factory=lambda: int(os.environ.get("POKER_RATE_LIMIT", 60)))
