"""A table runs hands one after another as an asyncio task.

It asks seated players for decisions (bots via the TurnRegistry, house bots
directly), enforces timeouts, paces the game for spectators and broadcasts
every public event on its EventBus.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from ..config import Settings
from ..engine.hand import Action, Hand, IllegalAction, SeatSpec, normalize_action
from ..store.db import Store
from .bus import EventBus
from .house import HouseBot
from .turns import TurnRegistry

log = logging.getLogger(__name__)

MAX_SEATS = 9


@dataclass
class Pacing:
    action: float = 2.0  # min seconds between two actions
    street: float = 1.5  # pause before flop/turn/river and before pots are pushed
    hand_end: float = 4.0  # pause after a hand before the next one starts

    @classmethod
    def fast(cls) -> "Pacing":
        return cls(0.0, 0.0, 0.0)

    def to_dict(self) -> dict[str, float]:
        return {"action": self.action, "street": self.street, "hand_end": self.hand_end}


@dataclass
class Blinds:
    small: int
    big: int
    ante: int
    level: int  # 1-based
    hands_left: int  # hands until the next level (including the current one)

    def to_dict(self) -> dict[str, int]:
        return {"small": self.small, "big": self.big, "ante": self.ante,
                "level": self.level, "hands_until_next_level": self.hands_left}


@dataclass
class SeatState:
    seat: int
    player_id: str
    name: str
    stack: int
    house: HouseBot | None = None
    sitting_out: bool = False
    disconnected: bool = False
    timeouts: int = 0

    @property
    def status(self) -> str:
        if self.stack <= 0:
            return "busted"
        if self.disconnected:
            return "disconnected"
        if self.sitting_out:
            return "sitting_out"
        return "active"

    def to_dict(self) -> dict[str, Any]:
        return {"seat": self.seat, "name": self.name, "stack": self.stack,
                "status": self.status, "house": self.house is not None}


HandEndHook = Callable[["Table", Hand], Awaitable[None]]
EventHook = Callable[["Table", dict[str, Any]], None]


@dataclass
class Table:
    id: str
    kind: str  # "tournament" | "practice"
    title: str
    seats: dict[int, SeatState]
    store: Store
    registry: TurnRegistry
    settings: Settings
    blinds_for: Callable[[int], Blinds]
    pacing: Pacing = field(default_factory=Pacing)
    tournament_id: int | None = None
    button_seat: int | None = None
    hand_no: int = 0
    on_hand_end: HandEndHook | None = None
    on_event: EventHook | None = None  # sees every public event (tournaments: Discord commentary)
    max_hands: int | None = None
    owner_bot_id: str | None = None  # practice tables: the bot that started it

    bus: EventBus = field(default_factory=EventBus)
    status: str = "waiting"  # waiting | running | finished
    hand: Hand | None = None
    blinds: Blinds | None = None
    waiting_on: dict[str, Any] | None = None
    finish_reason: str | None = None
    created_at: float = field(default_factory=time.time)
    _published: int = 0
    _stop: bool = False
    task: asyncio.Task[None] | None = None

    # ------------------------------------------------------------------ public views

    @property
    def practice(self) -> bool:
        return self.kind == "practice"

    def alive_seats(self) -> list[SeatState]:
        return [s for s in sorted(self.seats.values(), key=lambda s: s.seat) if s.stack > 0]

    def snapshot(self) -> dict[str, Any]:
        waiting = None
        if self.waiting_on:
            waiting = {
                "seat": self.waiting_on["seat"],
                "remaining_ms": max(0, int((self.waiting_on["deadline"] - time.monotonic()) * 1000)),
            }
        return {
            "id": self.id,
            "kind": self.kind,
            "title": self.title,
            "tournament_id": self.tournament_id,
            "status": self.status,
            "finish_reason": self.finish_reason,
            "hand_no": self.hand_no,
            "hand_id": self.hand.hand_id if self.hand else None,
            "blinds": self.blinds.to_dict() if self.blinds else None,
            "button": self.button_seat,
            "seats": [s.to_dict() for s in sorted(self.seats.values(), key=lambda s: s.seat)],
            "events": self.hand.public_events() if self.hand else [],
            "waiting_on": waiting,
            "pacing": self.pacing.to_dict(),
            "spectators": self.bus.subscriber_count,
        }

    def summary(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "title": self.title,
            "tournament_id": self.tournament_id,
            "status": self.status,
            "hand_no": self.hand_no,
            "players": [s.name for s in self.alive_seats()],
            "blinds": self.blinds.to_dict() if self.blinds else None,
        }

    def broadcast(self, event: dict[str, Any]) -> None:
        self.bus.publish(event)
        if self.on_event:
            self.on_event(self, event)

    # ------------------------------------------------------------------ lifecycle

    def start(self) -> None:
        self.task = asyncio.create_task(self.run(), name=f"table-{self.id}")

    def stop(self, reason: str) -> None:
        self._stop = True
        self.finish_reason = reason
        if self.task and not self.task.done():
            self.task.cancel()

    async def run(self) -> None:
        self.status = "running"
        self.broadcast({"type": "table_status", "status": "running"})
        try:
            while not self._stop and len(self.alive_seats()) >= 2:
                if self.max_hands is not None and self.hand_no >= self.max_hands:
                    self.finish_reason = self.finish_reason or "hand limit reached"
                    break
                hand = await self._play_hand()
                if self.on_hand_end:
                    await self.on_hand_end(self, hand)
                await self._sleep(self.pacing.hand_end)
        except asyncio.CancelledError:
            if self.hand and not self.hand.done:
                self.store.db.execute("DELETE FROM hands WHERE id = ?", (self.hand.hand_id,))
            raise
        except Exception:
            log.exception("table %s crashed", self.id)
            self.finish_reason = "internal error"
            raise
        finally:
            self.status = "finished"
            self.waiting_on = None
            self.broadcast({"type": "table_status", "status": "finished", "reason": self.finish_reason})

    # ------------------------------------------------------------------ hands

    def _next_button(self) -> int:
        alive = [s.seat for s in self.alive_seats()]
        if self.button_seat is None:
            return random.choice(alive)
        for k in range(1, MAX_SEATS + 1):
            seat = (self.button_seat + k) % MAX_SEATS
            if seat in alive:
                return seat
        return alive[0]

    async def _play_hand(self) -> Hand:
        self.blinds = self.blinds_for(self.hand_no)
        self.button_seat = self._next_button()
        hand_id = self.store.begin_hand(self.id, self.tournament_id, self.practice, self.hand_no + 1)
        specs = [SeatSpec(s.seat, s.player_id, s.name, s.stack) for s in self.alive_seats()]
        hand = Hand(hand_id, specs, self.button_seat, self.blinds.small, self.blinds.big, self.blinds.ante)
        hand.events[0]["hand_no"] = self.hand_no + 1
        hand.events[0]["level"] = self.blinds.level
        self.hand = hand
        self.hand_no += 1
        self._published = 0
        await self._publish_new(hand)

        last = time.monotonic()
        while not hand.done:
            player = hand.to_act
            assert player is not None
            action = await self._decide(self.seats[player.seat], hand)
            wait = last + self.pacing.action - time.monotonic()
            await self._sleep(wait)
            hand.apply(action)
            await self._publish_new(hand)
            last = time.monotonic()

        for p in hand.players:
            self.seats[p.seat].stack = p.stack
        bot_results = [(p.player_id, p.seat, p.stack - p.start_stack)
                       for p in hand.players if self.seats[p.seat].house is None]
        self.store.finish_hand(hand_id, hand.events, self.practice, bot_results)
        return hand

    async def _publish_new(self, hand: Hand) -> None:
        new = hand.events[self._published:]
        self._published = len(hand.events)
        for ev in new:
            if ev["type"] == "street" or (ev["type"] == "win" and hand.revealed):
                await self._sleep(self.pacing.street)
            if ev["type"] == "deal_hole":
                continue
            self.broadcast(ev)

    async def _sleep(self, seconds: float) -> None:
        await asyncio.sleep(max(0.0, seconds))

    # ------------------------------------------------------------------ decisions

    def _status_event(self, hand: Hand, seat: SeatState, status: str) -> None:
        hand.events.append({"type": "player_status", "seat": seat.seat, "name": seat.name, "status": status})

    def turn_state(self, hand: Hand, legal: dict[str, Any]) -> dict[str, Any]:
        p = hand.to_act
        assert p is not None and self.blinds is not None
        return {
            "table_id": self.id,
            "tournament_id": self.tournament_id,
            "practice": self.practice,
            "hand_id": hand.hand_id,
            "hand_no": self.hand_no,
            "seat": p.seat,
            "name": p.name,
            "hole_cards": list(p.hole),
            "stack": p.stack,
            "bet": p.bet,
            "street": hand.street,
            "board": list(hand.board),
            "pot": hand.pot,
            "current_bet": hand.current_bet,
            "to_call": legal["call"] or 0,
            "legal": legal,
            "blinds": self.blinds.to_dict(),
            "button": self.button_seat,
            "players": [{**hand.player_view(q), "is_you": q is p} for q in hand.players],
            "action_log": hand.public_events(),
        }

    @staticmethod
    def _auto(legal: dict[str, Any]) -> Action:
        return Action("check") if legal["check"] else Action("fold")

    async def _decide(self, seat: SeatState, hand: Hand) -> Action:
        legal = hand.legal_actions()
        state = self.turn_state(hand, legal)

        if seat.house is not None:
            await asyncio.sleep(0)
            proposal = seat.house.decide(state)
            try:
                return normalize_action(legal, proposal.kind, proposal.amount)
            except IllegalAction:
                return self._auto(legal)

        bot_id = seat.player_id
        if not self.registry.is_connected(bot_id):
            if not seat.disconnected:
                seat.disconnected = True
                self._status_event(hand, seat, "disconnected")
                await self._publish_new(hand)
            return self._auto(legal)
        if seat.disconnected:
            seat.disconnected = False
            self._status_event(hand, seat, "connected")

        timeout = self.settings.sitout_grace if seat.sitting_out else self.settings.decision_timeout
        turn = self.registry.open_turn(bot_id, self.id, state, legal, timeout)
        self.waiting_on = {"seat": seat.seat, "deadline": turn.deadline}
        self.broadcast({"type": "turn", "seat": seat.seat, "name": seat.name, "timeout_ms": int(timeout * 1000)})
        try:
            action = await asyncio.wait_for(turn.future, timeout)
            seat.timeouts = 0
            if seat.sitting_out:
                seat.sitting_out = False
                self._status_event(hand, seat, "back")
            return action
        except TimeoutError:
            seat.timeouts += 1
            self._status_event(hand, seat, "timeout")
            if not seat.sitting_out and seat.timeouts >= self.settings.max_timeouts:
                seat.sitting_out = True
                self._status_event(hand, seat, "sitting_out")
            await self._publish_new(hand)
            return self._auto(legal)
        finally:
            self.waiting_on = None
            self.registry.close_turn(turn)
