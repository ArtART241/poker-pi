"""Connects table runners (which need decisions) with bots (which long-poll for turns)."""

from __future__ import annotations

import asyncio
import secrets
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

from ..engine.hand import Action, IllegalAction, normalize_action


class TurnError(Exception):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


@dataclass
class Turn:
    id: str
    bot_id: str
    table_id: str
    payload: dict[str, Any]
    legal: dict[str, Any]
    deadline: float  # time.monotonic()
    future: asyncio.Future[Action] = field(repr=False)

    def public_payload(self) -> dict[str, Any]:
        remaining = max(0, int((self.deadline - time.monotonic()) * 1000))
        return {**self.payload, "turn_id": self.id, "deadline_ms": remaining}


@dataclass
class Presence:
    last_seen: float = 0.0
    waiting: int = 0
    wakeup: asyncio.Event = field(default_factory=asyncio.Event)


class TurnRegistry:
    def __init__(self, disconnect_after: float) -> None:
        self.disconnect_after = disconnect_after
        self._turns: dict[str, Turn] = {}
        self._presence: dict[str, Presence] = {}
        # turn_id -> (bot_id, accepted action, what the bot actually sent)
        self._answered: OrderedDict[str, tuple[str, Action, tuple[Any, Any]]] = OrderedDict()

    def _pres(self, bot_id: str) -> Presence:
        p = self._presence.get(bot_id)
        if p is None:
            p = self._presence[bot_id] = Presence()
        return p

    # ------------------------------------------------------------------ bot side

    def seen(self, bot_id: str) -> None:
        self._pres(bot_id).last_seen = time.monotonic()

    def is_connected(self, bot_id: str) -> bool:
        p = self._presence.get(bot_id)
        if p is None:
            return False
        return p.waiting > 0 or time.monotonic() - p.last_seen < self.disconnect_after

    def last_seen(self, bot_id: str) -> float:
        p = self._presence.get(bot_id)
        return p.last_seen if p else 0.0

    def open_turns(self, bot_id: str, table_id: str | None = None) -> list[Turn]:
        return [t for t in self._turns.values()
                if t.bot_id == bot_id and not t.future.done()
                and (table_id is None or t.table_id == table_id)]

    async def wait_for_turn(self, bot_id: str, wait: float, table_id: str | None = None) -> Turn | None:
        pres = self._pres(bot_id)
        pres.last_seen = time.monotonic()
        end = pres.last_seen + wait
        pres.waiting += 1
        try:
            while True:
                turns = self.open_turns(bot_id, table_id)
                if turns:
                    return min(turns, key=lambda t: t.deadline)
                remaining = end - time.monotonic()
                if remaining <= 0:
                    return None
                pres.wakeup.clear()
                try:
                    await asyncio.wait_for(pres.wakeup.wait(), remaining)
                except TimeoutError:
                    return None
        finally:
            pres.waiting -= 1
            pres.last_seen = time.monotonic()

    def submit(self, bot_id: str, turn_id: str, kind: str, amount: Any) -> Action:
        done = self._answered.get(turn_id)
        if done and done[0] == bot_id:
            if done[2] == (kind, amount):
                return done[1]  # same answer sent twice (e.g. a retry): fine
            raise TurnError(409, "this turn was already answered with a different action")
        turn = self._turns.get(turn_id)
        if turn is None:
            raise TurnError(409, "this turn is no longer open (already answered, timed out, or unknown turn_id)")
        if turn.bot_id != bot_id:
            raise TurnError(403, "this turn belongs to another bot")
        if turn.future.done():
            raise TurnError(409, "this turn is no longer open")
        try:
            action = normalize_action(turn.legal, kind, amount)
        except IllegalAction as e:
            raise TurnError(422, str(e)) from None
        turn.future.set_result(action)
        self._answered[turn_id] = (bot_id, action, (kind, amount))
        while len(self._answered) > 2000:
            self._answered.popitem(last=False)
        return action

    # ------------------------------------------------------------------ table side

    def open_turn(self, bot_id: str, table_id: str, payload: dict[str, Any],
                  legal: dict[str, Any], timeout: float) -> Turn:
        turn = Turn(
            id="t_" + secrets.token_hex(8),
            bot_id=bot_id,
            table_id=table_id,
            payload=payload,
            legal=legal,
            deadline=time.monotonic() + timeout,
            future=asyncio.get_running_loop().create_future(),
        )
        self._turns[turn.id] = turn
        self._pres(bot_id).wakeup.set()
        return turn

    def close_turn(self, turn: Turn) -> None:
        self._turns.pop(turn.id, None)
        if not turn.future.done():
            turn.future.cancel()
