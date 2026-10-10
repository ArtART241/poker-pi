"""Read-only endpoints without authentication. They feed the spectator website.

Nothing here reveals hole cards of a hand that is still being played.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from ..services import Hub
from . import models as M
from .deps import get_hub
from .views import tournament_detail, tournament_info

router = APIRouter(prefix="/api/v1/public", tags=["Public (spectators)"])


@router.get("/tournaments", response_model=list[M.TournamentInfo], summary="All tournaments, newest first")
async def tournaments(hub: Hub = Depends(get_hub)) -> list[dict[str, Any]]:
    return [tournament_info(hub, t) for t in hub.store.list_tournaments(limit=100)]


@router.get("/tournaments/{tournament_id}", summary="Tournament details, standings and results",
            responses={404: {"model": M.Error}})
async def tournament(tournament_id: int, hub: Hub = Depends(get_hub)) -> dict[str, Any]:
    t = hub.store.get_tournament(tournament_id)
    if t is None:
        raise HTTPException(404, "No such tournament.")
    return tournament_detail(hub, t)


@router.get("/tables", summary="Tables that are running (or finished recently)")
async def tables(hub: Hub = Depends(get_hub)) -> list[dict[str, Any]]:
    order = {"running": 0, "waiting": 1, "finished": 2}
    return sorted((t.summary() for t in hub.tables.values()),
                  key=lambda t: (order.get(t["status"], 3), t["kind"] != "tournament", t["id"]))


@router.get("/tables/{table_id}", summary="Current state of a table (no hidden cards)",
            responses={404: {"model": M.Error}})
async def table(table_id: str, hub: Hub = Depends(get_hub)) -> dict[str, Any]:
    t = hub.tables.get(table_id)
    if t is None:
        raise HTTPException(404, "No such table (or it is not running any more).")
    return t.snapshot()


def _sse(data: dict[str, Any]) -> str:
    return f"data: {json.dumps(data, separators=(',', ':'))}\n\n"


@router.get(
    "/tables/{table_id}/stream",
    summary="Live events of a table (Server-Sent Events)",
    responses={200: {"content": {"text/event-stream": {}}}, 404: {"model": M.Error}},
)
async def stream(table_id: str, request: Request, hub: Hub = Depends(get_hub)) -> StreamingResponse:
    """A never-ending `text/event-stream` response. The first message is a `snapshot`
    (same as `GET /tables/{id}`), then one message per event. A comment line is sent
    every 15 seconds to keep the connection alive."""
    t = hub.tables.get(table_id)
    if t is None:
        raise HTTPException(404, "No such table.")
    queue = t.bus.subscribe()

    async def events() -> AsyncIterator[str]:
        try:
            yield "retry: 3000\n" + _sse({"type": "snapshot", "table": t.snapshot()})
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), 15)
                except TimeoutError:
                    yield ": keep-alive\n\n"
                    continue
                yield _sse(event)
                if event["type"] == "table_status" and event.get("status") == "finished":
                    yield _sse({"type": "snapshot", "table": t.snapshot()})
        finally:
            t.bus.unsubscribe(queue)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/hands", response_model=list[M.HandSummary], summary="Finished hands (newest first)")
async def hands(
    table_id: str | None = None,
    tournament_id: int | None = None,
    bot: str | None = Query(None, description="Bot name"),
    before: int | None = Query(None, description="Only hands with an id smaller than this (paging)."),
    limit: int = Query(50, ge=1, le=200),
    hub: Hub = Depends(get_hub),
) -> list[dict[str, Any]]:
    bot_id = None
    if bot:
        row = hub.store.get_bot_by_name(bot)
        if row is None:
            return []
        bot_id = row["id"]
    return hub.store.list_hands(table_id=table_id, tournament_id=tournament_id, bot_id=bot_id,
                                before=before, limit=limit)


@router.get("/hands/{hand_id}", response_model=M.HandDetail, summary="Full replay of a finished hand",
            responses={404: {"model": M.Error}})
async def hand(hand_id: int, hub: Hub = Depends(get_hub)) -> dict[str, Any]:
    h = hub.store.get_hand(hand_id)
    if h is None:
        raise HTTPException(404, "Unknown hand, or the hand is still being played.")
    return h


@router.get("/leaderboard", summary="All-time tournament leaderboard")
async def leaderboard(hub: Hub = Depends(get_hub)) -> list[dict[str, Any]]:
    rows = hub.store.leaderboard()
    for r in rows:
        r["avg_place"] = round(r["avg_place"], 2) if r["avg_place"] is not None else None
    return rows


@router.get("/bots", summary="All registered bots")
async def bots(hub: Hub = Depends(get_hub)) -> list[dict[str, Any]]:
    return [
        {"name": b["name"], "owner": b["owner"], "created_at": b["created_at"],
         "connected": hub.registry.is_connected(b["id"])}
        for b in hub.store.list_bots()
    ]


@router.get("/bots/{name}", summary="Profile and statistics of a bot", responses={404: {"model": M.Error}})
async def bot_profile(name: str, hub: Hub = Depends(get_hub)) -> dict[str, Any]:
    b = hub.store.get_bot_by_name(name)
    if b is None or b["revoked"]:
        raise HTTPException(404, "No such bot.")
    seated = [
        {"table_id": t.id, "kind": t.kind, "title": t.title}
        for t in hub.tables.values()
        if t.status == "running" and any(s.player_id == b["id"] for s in t.seats.values())
    ]
    return {
        "name": b["name"],
        "owner": b["owner"],
        "created_at": b["created_at"],
        "connected": hub.registry.is_connected(b["id"]),
        "tables": seated,
        "stats": hub.store.bot_stats(b["id"]),
    }
