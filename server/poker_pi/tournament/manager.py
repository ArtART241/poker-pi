"""Starts scheduled tournaments, tracks eliminations and placements, runs practice tables."""

from __future__ import annotations

import asyncio
import logging
import random
import secrets
import time
from functools import partial
from typing import TYPE_CHECKING, Any

from ..engine.hand import Hand
from ..store.db import now_iso
from ..tables.house import HOUSE_KINDS, HouseBot
from ..tables.table import MAX_SEATS, Pacing, SeatState, Table
from .blinds import blinds_for, full_config

if TYPE_CHECKING:
    from ..services import Hub

log = logging.getLogger(__name__)


def spread_seats(n: int) -> list[int]:
    """n players spread evenly around a 9-seat table."""
    return [int(i * MAX_SEATS / n) for i in range(n)]


class TournamentManager:
    def __init__(self, hub: "Hub") -> None:
        self.hub = hub
        self.places: dict[int, dict[str, int]] = {}

    @staticmethod
    def table_id(tid: int) -> str:
        return f"t{tid}"

    # ------------------------------------------------------------------ scheduler

    async def scheduler_loop(self) -> None:
        while True:
            try:
                self.tick()
            except Exception:
                log.exception("scheduler tick failed")
            await asyncio.sleep(self.hub.settings.scheduler_interval)

    def tick(self) -> None:
        store, tables = self.hub.store, self.hub.tables
        now = now_iso()
        for t in store.list_tournaments(["registering", "running"]):
            table = tables.get(self.table_id(t["id"]))
            if t["status"] == "registering" and t["start_at"] <= now:
                self.start(t)
            elif t["status"] == "running":
                if table is None:
                    self.resume(t)
                elif table.status == "finished" and table.finish_reason == "internal error":
                    store.update_tournament(t["id"], status="cancelled", note="stopped by an internal error",
                                            finished_at=now_iso())
        # tournaments cancelled from the admin CLI while running
        for table in list(tables.values()):
            if table.kind == "tournament" and table.status == "running":
                t = store.get_tournament(table.tournament_id)  # type: ignore[arg-type]
                if t and t["status"] == "cancelled":
                    table.stop("cancelled by the admin")
        self.hub.practice.cleanup()

    # ------------------------------------------------------------------ start / resume

    def start(self, t: dict[str, Any]) -> None:
        store = self.hub.store
        cfg = full_config(t["config"])
        regs = store.registrations(t["id"])[: cfg["max_players"]]
        if len(regs) < 2:
            store.update_tournament(t["id"], status="cancelled",
                                    note="not enough players (at least 2 needed)", finished_at=now_iso())
            log.info("tournament %s cancelled: not enough players", t["id"])
            return
        random.shuffle(regs)
        seats = {
            seat: SeatState(seat, bot["id"], bot["name"], cfg["starting_stack"])
            for seat, bot in zip(spread_seats(len(regs)), regs)
        }
        self.places[t["id"]] = {}
        store.update_tournament(t["id"], status="running", started_at=now_iso(),
                                state=self._state(seats, None, 0, {}))
        log.info("tournament %s started with %d bots", t["id"], len(seats))
        self._launch(t, cfg, seats, button=None, hand_no=0)

    def resume(self, t: dict[str, Any]) -> None:
        state = t["state"] or {}
        cfg = full_config(t["config"])
        seats = {
            s["seat"]: SeatState(s["seat"], s["bot_id"], s["name"], s["stack"])
            for s in state.get("seats", []) if s["stack"] > 0
        }
        self.places[t["id"]] = dict(state.get("places", {}))
        log.info("tournament %s resumed at hand %s", t["id"], state.get("hand_no"))
        self._launch(t, cfg, seats, button=state.get("button"), hand_no=state.get("hand_no", 0))

    def _launch(self, t: dict[str, Any], cfg: dict[str, Any], seats: dict[int, SeatState],
                button: int | None, hand_no: int) -> None:
        table = Table(
            id=self.table_id(t["id"]),
            kind="tournament",
            title=t["name"],
            seats=seats,
            store=self.hub.store,
            registry=self.hub.registry,
            settings=self.hub.settings,
            blinds_for=partial(blinds_for, cfg["levels"], cfg["hands_per_level"]),
            pacing=Pacing(**cfg["pacing"]),
            tournament_id=t["id"],
            button_seat=button,
            hand_no=hand_no,
            on_hand_end=self._on_hand_end,
            on_event=self.hub.commentator.on_event,
        )
        self.hub.tables[table.id] = table
        table.start()

    @staticmethod
    def _state(seats: dict[int, SeatState], button: int | None, hand_no: int,
               places: dict[str, int]) -> dict[str, Any]:
        return {
            "seats": [{"seat": s.seat, "bot_id": s.player_id, "name": s.name, "stack": s.stack}
                      for s in seats.values()],
            "button": button,
            "hand_no": hand_no,
            "places": places,
        }

    # ------------------------------------------------------------------ after every hand

    async def _on_hand_end(self, table: Table, hand: Hand) -> None:
        tid = table.tournament_id
        assert tid is not None
        places = self.places.setdefault(tid, {})
        busted = [s for s in table.seats.values() if s.stack <= 0]
        if busted:
            start_stack = {p.seat: p.start_stack for p in hand.players}
            # bigger stack at the start of the hand = better place
            busted.sort(key=lambda s: (-start_stack.get(s.seat, 0), s.seat))
            first_place = len(table.seats) - len(busted) + 1
            for k, s in enumerate(busted):
                places[s.player_id] = first_place + k
                del table.seats[s.seat]
                table.broadcast({"type": "eliminated", "seat": s.seat, "name": s.name,
                                 "place": first_place + k})

        alive = table.alive_seats()
        store = self.hub.store
        if len(alive) <= 1:
            if alive:
                places[alive[0].player_id] = 1
            store.save_results(tid, places)
            store.update_tournament(tid, status="finished", finished_at=now_iso(),
                                    state=self._state(table.seats, table.button_seat, table.hand_no, places))
            winner = alive[0].name if alive else None
            table.finish_reason = f"{winner} wins the tournament" if winner else "finished"
            table.broadcast({"type": "tournament_end", "winner": winner,
                             "results": store.results(tid)})
            table._stop = True
            log.info("tournament %s finished, winner %s", tid, winner)
        else:
            store.update_tournament(tid, state=self._state(table.seats, table.button_seat,
                                                             table.hand_no, places))


class PracticeManager:
    """Private tables against house bots, started by a bot through the API."""

    MAX_HANDS = 300
    KEEP_FINISHED = 15 * 60  # seconds a finished practice table stays visible

    def __init__(self, hub: "Hub") -> None:
        self.hub = hub

    def for_bot(self, bot_id: str) -> Table | None:
        tables = [t for t in self.hub.tables.values()
                  if t.kind == "practice" and t.owner_bot_id == bot_id]
        running = [t for t in tables if t.status != "finished"]
        return running[0] if running else (max(tables, key=lambda t: t.created_at) if tables else None)

    def start(self, bot: dict[str, Any], opponents: list[str], speed: str,
              starting_stack: int = 1500) -> Table:
        old = self.for_bot(bot["id"])
        if old and old.status != "finished":
            old.stop("replaced by a new practice table")

        names: dict[str, int] = {}
        players: list[tuple[str, str, HouseBot | None]] = [(bot["id"], bot["name"], None)]
        for kind in opponents:
            names[kind] = names.get(kind, 0) + 1
            label = HOUSE_KINDS[kind] + ("" if names[kind] == 1 else f" {names[kind]}")
            players.append((f"house:{kind}:{names[kind]}", label, HouseBot(kind)))
        random.shuffle(players)
        seats = {
            seat: SeatState(seat, pid, name, starting_stack, house=house)
            for seat, (pid, name, house) in zip(spread_seats(len(players)), players)
        }
        cfg = full_config(None)
        pacing = Pacing(**cfg["pacing"]) if speed == "live" else Pacing.fast()
        table = Table(
            id="p_" + secrets.token_hex(3),
            kind="practice",
            title=f"Practice: {bot['name']}",
            seats=seats,
            store=self.hub.store,
            registry=self.hub.registry,
            settings=self.hub.settings,
            blinds_for=partial(blinds_for, cfg["levels"], cfg["hands_per_level"]),
            pacing=pacing,
            on_hand_end=self._on_hand_end,
            max_hands=self.MAX_HANDS,
            owner_bot_id=bot["id"],
        )
        self.hub.tables[table.id] = table
        table.start()
        return table

    async def _on_hand_end(self, table: Table, hand: Hand) -> None:
        owner = next((s for s in table.seats.values() if s.player_id == table.owner_bot_id), None)
        if owner is None or owner.stack <= 0:
            table.finish_reason = "your bot busted"
            table._stop = True
            return
        for s in [s for s in table.seats.values() if s.stack <= 0]:
            del table.seats[s.seat]
            table.broadcast({"type": "eliminated", "seat": s.seat, "name": s.name, "place": None})
        if len(table.seats) == 1:
            table.finish_reason = "your bot won"
            table._stop = True
        elif not self.hub.registry.is_connected(owner.player_id):
            table.finish_reason = "your bot disconnected"
            table._stop = True

    def stop(self, bot_id: str) -> Table | None:
        table = self.for_bot(bot_id)
        if table and table.status != "finished":
            table.stop("stopped by the bot")
        return table

    def cleanup(self) -> None:
        cutoff = time.time() - self.KEEP_FINISHED
        for tid, t in list(self.hub.tables.items()):
            if t.kind == "practice" and t.status == "finished" and t.created_at < cutoff:
                del self.hub.tables[tid]
