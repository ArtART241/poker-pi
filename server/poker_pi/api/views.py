"""Helpers that turn store rows / tables into API responses (shared by bot + public routes)."""

from __future__ import annotations

from typing import Any

from ..services import Hub
from ..tournament.blinds import full_config


def tournament_info(hub: Hub, t: dict[str, Any], bot_id: str | None = None) -> dict[str, Any]:
    cfg = full_config(t["config"])
    regs = hub.store.registrations(t["id"])
    results = hub.store.results(t["id"]) if t["status"] == "finished" else []
    info = {
        "id": t["id"],
        "name": t["name"],
        "status": t["status"],
        "start_at": t["start_at"],
        "started_at": t["started_at"],
        "finished_at": t["finished_at"],
        "note": t["note"],
        "table_id": hub.tournaments.table_id(t["id"]),
        "players": [r["name"] for r in regs],
        "max_players": cfg["max_players"],
        "starting_stack": cfg["starting_stack"],
        "hands_per_level": cfg["hands_per_level"],
        "winner": results[0]["name"] if results and results[0]["place"] == 1 else None,
    }
    if bot_id is not None:
        info["registered"] = any(r["id"] == bot_id for r in regs)
    return info


def tournament_detail(hub: Hub, t: dict[str, Any]) -> dict[str, Any]:
    cfg = full_config(t["config"])
    info = tournament_info(hub, t)
    info["config"] = {**cfg, "levels": [list(level) for level in cfg["levels"]]}
    info["results"] = hub.store.results(t["id"])
    state = t["state"] or {}
    places: dict[str, int] = state.get("places", {})
    alive = [{"name": s["name"], "stack": s["stack"], "place": None}
             for s in sorted(state.get("seats", []), key=lambda s: -s["stack"])
             if s["bot_id"] not in places]
    stack_of = {s["bot_id"]: s["stack"] for s in state.get("seats", [])}
    out = []
    for bot_id, place in sorted(places.items(), key=lambda kv: kv[1]):
        bot = hub.store.get_bot(bot_id)
        out.append({"name": bot["name"] if bot else bot_id, "stack": stack_of.get(bot_id, 0), "place": place})
    winners = [o for o in out if o["place"] == 1]
    info["standings"] = winners + alive + [o for o in out if o["place"] != 1]
    table = hub.tables.get(info["table_id"])
    info["live"] = bool(table and table.status == "running")
    return info
