"""Built-in opponents for practice tables. They run inside the server, no HTTP involved."""

from __future__ import annotations

import random
from typing import Any

from ..engine import cards as C
from ..engine.hand import Action

HOUSE_KINDS = {
    "random": "Randy Random",
    "station": "Carl Callstation",
    "tight": "Tina Tight",
}


def chen_score(hole: list[str]) -> float:
    """Bill Chen's preflop hand strength formula (roughly -1 .. 20)."""
    values = {r: v for r, v in zip("23456789TJQKA", (1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 6, 7, 8, 10))}
    order = "23456789TJQKA"
    r1, r2 = sorted((c[0] for c in hole), key=order.index, reverse=True)
    score = values[r1]
    if r1 == r2:
        return max(score * 2, 5)
    if hole[0][1] == hole[1][1]:
        score += 2
    gap = order.index(r1) - order.index(r2) - 1
    score -= {0: 0, 1: 1, 2: 2, 3: 4}.get(gap, 5)
    if gap <= 1 and order.index(r1) < order.index("Q"):
        score += 1
    return score


class HouseBot:
    def __init__(self, kind: str) -> None:
        if kind not in HOUSE_KINDS:
            raise ValueError(f"unknown house bot {kind!r}")
        self.kind = kind
        self.rng = random.Random()

    def decide(self, state: dict[str, Any]) -> Action:
        return getattr(self, f"_{self.kind}")(state)

    # calls everything, never raises
    def _station(self, s: dict[str, Any]) -> Action:
        return Action("check") if s["legal"]["check"] else Action("call")

    def _random(self, s: dict[str, Any]) -> Action:
        legal = s["legal"]
        roll = self.rng.random()
        if legal["raise"] and roll < 0.2:
            lo, hi = legal["raise"]["min"], legal["raise"]["max"]
            to = lo if self.rng.random() < 0.7 else self.rng.randint(lo, hi)
            return Action("raise", to)
        if legal["check"]:
            return Action("check")
        if roll < 0.35:
            return Action("fold")
        return Action("call")

    def _tight(self, s: dict[str, Any]) -> Action:
        legal, hole, board = s["legal"], s["hole_cards"], s["board"]
        pot, bb = s["pot"], s["blinds"]["big"]
        to_call = legal["call"] or 0

        if not board:
            strength = chen_score(hole)
            if strength >= 10 and legal["raise"] and s["current_bet"] <= 4 * bb:
                return self._raise_to(legal, s["current_bet"] + 3 * bb)
            if strength >= 10:
                return self._passive(legal)
            if strength >= 7 and to_call <= 4 * bb:
                return self._passive(legal)
            if to_call <= bb // 2 and strength >= 5:
                return self._passive(legal)
            return Action("check") if legal["check"] else Action("fold")

        rank_class = C._evaluator.get_rank_class(C.evaluate(hole, board))
        if rank_class <= 7 and legal["raise"]:  # two pair or better
            return self._raise_to(legal, s["current_bet"] + max(pot * 3 // 4, bb))
        if rank_class == 8 and to_call <= pot // 2:  # one pair
            return self._passive(legal)
        if legal["check"]:
            return Action("check")
        return Action("call") if to_call <= pot // 10 else Action("fold")

    @staticmethod
    def _passive(legal: dict[str, Any]) -> Action:
        return Action("check") if legal["check"] else Action("call")

    @staticmethod
    def _raise_to(legal: dict[str, Any], target: int) -> Action:
        rng = legal["raise"]
        return Action("raise", max(rng["min"], min(rng["max"], target)))
