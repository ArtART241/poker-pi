"""Endpoints for bots. Every request needs `Authorization: Bearer <token>`."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from ..services import Hub
from ..tables.turns import TurnError
from . import models as M
from .deps import current_bot, get_hub, refund
from .views import tournament_info

ERRORS = {
    401: {"model": M.Error, "description": "Missing, invalid or revoked token."},
    429: {"model": M.Error, "description": "Too many requests per second."},
}

router = APIRouter(prefix="/api/v1/bot", tags=["Bot API"], responses=ERRORS)

Bot = dict[str, Any]


@router.get("/me", response_model=M.MeResponse, summary="Who am I? (good first test of your token)")
async def me(bot: Bot = Depends(current_bot), hub: Hub = Depends(get_hub)) -> dict[str, Any]:
    tables = []
    for t in hub.tables.values():
        if t.status == "finished":
            continue
        for s in t.seats.values():
            if s.player_id == bot["id"]:
                tables.append({"table_id": t.id, "kind": t.kind, "seat": s.seat,
                               "stack": s.stack, "status": s.status})
    return {
        "id": bot["id"],
        "name": bot["name"],
        "owner": bot["owner"],
        "tables": tables,
        "open_turns": len(hub.registry.open_turns(bot["id"])),
        "registered_tournaments": hub.store.registered_tournaments(bot["id"]),
        "stats": hub.store.bot_stats(bot["id"]),
    }


@router.get(
    "/turn",
    response_model=M.TurnState,
    response_model_exclude_unset=True,  # events only carry the fields of their type
    summary="Wait until it is your turn (long-poll)",
    responses={204: {"description": "Not your turn within `wait` seconds. Just ask again."}},
)
async def get_turn(
    response: Response,
    wait: float = Query(25, ge=0, le=30, description="Seconds to wait for a turn before answering 204."),
    table_id: str | None = Query(None, description="Only wait for turns at this table."),
    bot: Bot = Depends(current_bot),
    hub: Hub = Depends(get_hub),
) -> Any:
    """Blocks until a decision is needed from your bot, then returns the full game state.

    If nothing happens within `wait` seconds the answer is **204 No Content** (empty body):
    simply call again. Bots typically run `while True: turn = GET /turn; POST /action`.
    """
    turn = await hub.registry.wait_for_turn(bot["id"], wait, table_id)
    if turn is None:
        return Response(status_code=204)
    refund(bot["id"])
    return turn.public_payload()


@router.post(
    "/action",
    response_model=M.ActionResponse,
    summary="Send your decision",
    responses={
        403: {"model": M.Error, "description": "The turn belongs to another bot."},
        409: {"model": M.Error, "description": "The turn is no longer open (answered, timed out, unknown)."},
        422: {"model": M.Error, "description": "The action is not legal right now (detail says why)."},
    },
)
async def post_action(body: M.ActionRequest, bot: Bot = Depends(current_bot),
                hub: Hub = Depends(get_hub)) -> dict[str, Any]:
    """`raise` means *raise TO*: `amount` is your total bet for this street, not the increase.

    Sending the exact same request twice (e.g. after a network hiccup) is safe.
    """
    try:
        action = hub.registry.submit(bot["id"], body.turn_id, body.action, body.amount)
    except TurnError as e:
        raise HTTPException(e.status, e.detail) from None
    refund(bot["id"])
    return {"accepted": True, "action": action.kind, "amount": action.amount}


@router.get("/tournaments", response_model=list[M.TournamentInfo], summary="Upcoming, running and recent tournaments")
async def list_tournaments(bot: Bot = Depends(current_bot), hub: Hub = Depends(get_hub)) -> list[dict[str, Any]]:
    return [tournament_info(hub, t, bot["id"]) for t in hub.store.list_tournaments(limit=30)]


@router.post(
    "/tournaments/{tournament_id}/register",
    response_model=M.RegistrationResponse,
    summary="Sign up for a tournament",
    responses={404: {"model": M.Error}, 409: {"model": M.Error, "description": "Registration closed or full."}},
)
async def register(tournament_id: int, bot: Bot = Depends(current_bot), hub: Hub = Depends(get_hub)) -> dict[str, Any]:
    t = hub.store.get_tournament(tournament_id)
    if t is None:
        raise HTTPException(404, "No such tournament.")
    if t["status"] != "registering":
        raise HTTPException(409, f"Registration is closed (tournament is {t['status']}).")
    regs = hub.store.registrations(tournament_id)
    max_players = t["config"].get("max_players", 9)
    if len(regs) >= max_players and not any(r["id"] == bot["id"] for r in regs):
        raise HTTPException(409, f"Tournament is full ({max_players} players).")
    hub.store.register(tournament_id, bot["id"])
    return {"tournament_id": tournament_id, "registered": True}


@router.delete(
    "/tournaments/{tournament_id}/register",
    response_model=M.RegistrationResponse,
    summary="Withdraw from a tournament (before it starts)",
    responses={404: {"model": M.Error}, 409: {"model": M.Error}},
)
async def unregister(tournament_id: int, bot: Bot = Depends(current_bot), hub: Hub = Depends(get_hub)) -> dict[str, Any]:
    t = hub.store.get_tournament(tournament_id)
    if t is None:
        raise HTTPException(404, "No such tournament.")
    if t["status"] != "registering":
        raise HTTPException(409, "The tournament already started; you cannot withdraw any more.")
    hub.store.unregister(tournament_id, bot["id"])
    return {"tournament_id": tournament_id, "registered": False}


def _practice_response(request: Request, table: Any) -> dict[str, Any]:
    base = str(request.base_url).rstrip("/")
    return {
        "table_id": table.id,
        "status": table.status,
        "finish_reason": table.finish_reason,
        "hand_no": table.hand_no,
        "players": [s.to_dict() for s in sorted(table.seats.values(), key=lambda s: s.seat)],
        "watch_url": f"{base}/#/table/{table.id}",
    }


@router.post("/practice", response_model=M.PracticeResponse, summary="Start a practice table against house bots")
async def start_practice(request: Request, body: M.PracticeRequest | None = None,
                   bot: Bot = Depends(current_bot), hub: Hub = Depends(get_hub)) -> dict[str, Any]:
    """Starts a private table for your bot against built-in opponents. Results do not count.

    The table ends when your bot busts, wins, stops polling, or after 300 hands.
    Starting a new practice table replaces the old one. Your turns arrive through the
    normal `GET /turn` loop.
    """
    body = body or M.PracticeRequest()
    opponents = [o.value for o in body.opponents] if body.opponents else ["random", "station", "tight"]
    speed = body.speed.value if body.speed else "fast"
    table = hub.practice.start(bot, opponents, speed, body.starting_stack or 1500)
    return _practice_response(request, table)


@router.get("/practice", response_model=M.PracticeResponse, summary="Your current (or last) practice table",
            responses={404: {"model": M.Error}})
async def get_practice(request: Request, bot: Bot = Depends(current_bot), hub: Hub = Depends(get_hub)) -> dict[str, Any]:
    table = hub.practice.for_bot(bot["id"])
    if table is None:
        raise HTTPException(404, "You have no practice table. Start one with POST /practice.")
    return _practice_response(request, table)


@router.delete("/practice", response_model=M.PracticeResponse, summary="Stop your practice table",
               responses={404: {"model": M.Error}})
async def stop_practice(request: Request, bot: Bot = Depends(current_bot), hub: Hub = Depends(get_hub)) -> dict[str, Any]:
    table = hub.practice.stop(bot["id"])
    if table is None:
        raise HTTPException(404, "You have no practice table.")
    return _practice_response(request, table)


@router.get("/hands", response_model=list[M.HandSummary], summary="Finished hands you played in")
async def my_hands(
    table_id: str | None = None,
    tournament_id: int | None = None,
    before: int | None = Query(None, description="Only hands with an id smaller than this (paging)."),
    limit: int = Query(50, ge=1, le=200),
    bot: Bot = Depends(current_bot),
    hub: Hub = Depends(get_hub),
) -> list[dict[str, Any]]:
    return hub.store.list_hands(table_id=table_id, tournament_id=tournament_id, bot_id=bot["id"],
                                before=before, limit=limit)


@router.get("/hands/{hand_id}", response_model=M.HandDetail, response_model_exclude_unset=True,
            summary="Full history of a finished hand", responses={404: {"model": M.Error}})
async def hand_detail(hand_id: int, bot: Bot = Depends(current_bot), hub: Hub = Depends(get_hub)) -> dict[str, Any]:
    """Includes every player's hole cards. Only available once the hand is over."""
    hand = hub.store.get_hand(hand_id)
    if hand is None:
        raise HTTPException(404, "Unknown hand, or the hand is still being played.")
    return hand
