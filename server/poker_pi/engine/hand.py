"""A single hand of No-Limit Texas Hold'em as a pure, synchronous state machine.

The hand knows nothing about networking, time or bots. You create it, ask who is
to act (`to_act`), ask what they may do (`legal_actions`) and feed actions in
(`apply`). Everything that happens is appended to `events`, a list of plain dicts
that is also the stored hand history.

Rules implemented:
- antes (dead money), small/big blind, heads-up blind order (button = small blind)
- "raise" always means "raise TO" a total street bet
- minimum raise = current bet + size of the last full raise (big blind at street start)
- an all-in raise smaller than a full raise does not reopen betting for players who
  already acted (unless several short raises add up to a full raise)
- uncalled bets are returned, side pots, split pots, odd chips go to the first winner
  left of the button
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from . import cards as C

STREETS = ("preflop", "flop", "turn", "river")


class IllegalAction(ValueError):
    """The submitted action is not allowed in the current state."""


@dataclass
class SeatSpec:
    seat: int
    player_id: str
    name: str
    stack: int


@dataclass
class PlayerState:
    seat: int
    player_id: str
    name: str
    stack: int
    start_stack: int
    hole: list[str] = field(default_factory=list)
    bet: int = 0  # chips put in on the current street
    committed: int = 0  # chips put in during the whole hand (incl. antes)
    folded: bool = False
    all_in: bool = False
    acted: bool = False  # acted voluntarily on this street
    acted_facing: int = 0  # current bet level right after this player's last action

    @property
    def status(self) -> str:
        if self.folded:
            return "folded"
        if self.all_in:
            return "all_in"
        return "active"


@dataclass(frozen=True)
class Action:
    kind: str  # "fold" | "check" | "call" | "raise"
    amount: int | None = None  # for raise: the total bet to raise to

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"action": self.kind}
        if self.amount is not None:
            d["amount"] = self.amount
        return d


class Hand:
    def __init__(
        self,
        hand_id: int,
        players: Iterable[SeatSpec],
        button_seat: int,
        small_blind: int,
        big_blind: int,
        ante: int = 0,
        deck: list[str] | None = None,
    ) -> None:
        specs = sorted(players, key=lambda p: p.seat)
        if len(specs) < 2:
            raise ValueError("a hand needs at least two players")
        if any(p.stack <= 0 for p in specs):
            raise ValueError("every player needs chips")
        if button_seat not in {p.seat for p in specs}:
            raise ValueError("button must sit on an occupied seat")

        self.hand_id = hand_id
        self.players = [
            PlayerState(p.seat, p.player_id, p.name, p.stack, p.stack) for p in specs
        ]
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.ante = ante
        self.deck = list(deck) if deck is not None else C.shuffled_deck()
        self.board: list[str] = []
        self.street = "preflop"
        self.current_bet = 0
        self.min_raise = big_blind  # size of the last full raise
        self.to_act_index: int | None = None
        self.done = False
        self.events: list[dict[str, Any]] = []
        self.revealed = False  # hole cards of live players have been shown

        self.button_index = next(i for i, p in enumerate(self.players) if p.seat == button_seat)
        n = len(self.players)
        if n == 2:
            self.sb_index = self.button_index
            self.bb_index = (self.button_index + 1) % n
        else:
            self.sb_index = (self.button_index + 1) % n
            self.bb_index = (self.button_index + 2) % n

        self._start()

    # ------------------------------------------------------------------ helpers

    def _emit(self, type_: str, **data: Any) -> None:
        self.events.append({"type": type_, **data})

    def _p(self, i: int) -> PlayerState:
        return self.players[i]

    def _seat_info(self, p: PlayerState) -> dict[str, Any]:
        return {"seat": p.seat, "name": p.name}

    def _draw(self, k: int) -> list[str]:
        out, self.deck = self.deck[:k], self.deck[k:]
        return out

    def _put_in(self, p: PlayerState, amount: int, *, as_bet: bool = True) -> int:
        amount = min(amount, p.stack)
        p.stack -= amount
        p.committed += amount
        if as_bet:
            p.bet += amount
        if p.stack == 0:
            p.all_in = True
        return amount

    @property
    def pot(self) -> int:
        """All chips in the middle, including bets of the current street."""
        return sum(p.committed for p in self.players)

    def _live(self) -> list[PlayerState]:
        return [p for p in self.players if not p.folded]

    def _can_act(self, p: PlayerState) -> bool:
        return not p.folded and not p.all_in

    def _needs_to_act(self, p: PlayerState) -> bool:
        return self._can_act(p) and (not p.acted or p.bet < self.current_bet)

    def _order_from(self, start: int) -> list[int]:
        n = len(self.players)
        return [(start + k) % n for k in range(n)]

    # ------------------------------------------------------------------ setup

    def _start(self) -> None:
        self._emit(
            "hand_start",
            hand_id=self.hand_id,
            button=self._p(self.button_index).seat,
            small_blind=self.small_blind,
            big_blind=self.big_blind,
            ante=self.ante,
            players=[
                {"seat": p.seat, "name": p.name, "player_id": p.player_id, "stack": p.stack}
                for p in self.players
            ],
        )
        if self.ante > 0:
            for p in self.players:
                amount = self._put_in(p, self.ante, as_bet=False)
                self._emit("post", **self._seat_info(p), blind="ante", amount=amount,
                           all_in=p.all_in)

        for idx, kind, size in ((self.sb_index, "small", self.small_blind),
                                (self.bb_index, "big", self.big_blind)):
            p = self._p(idx)
            if p.all_in:  # busted by the ante
                continue
            amount = self._put_in(p, size)
            self._emit("post", **self._seat_info(p), blind=kind, amount=amount, all_in=p.all_in)
        self.current_bet = self.big_blind

        # deal two cards each, one at a time, starting left of the button
        order = self._order_from(self.button_index + 1)
        for _ in range(2):
            for i in order:
                self._p(i).hole.extend(self._draw(1))
        for p in self.players:
            self._emit("deal_hole", **self._seat_info(p), cards=list(p.hole))

        self._continue_from(self.bb_index + 1)

    # ------------------------------------------------------------------ queries

    @property
    def to_act(self) -> PlayerState | None:
        return None if self.to_act_index is None else self._p(self.to_act_index)

    def player_by_seat(self, seat: int) -> PlayerState:
        for p in self.players:
            if p.seat == seat:
                return p
        raise KeyError(seat)

    def legal_actions(self) -> dict[str, Any]:
        """What the player to act may do.

        `call` is the number of chips calling adds (None if there is nothing to call),
        `raise` the allowed range of total bets to raise to (None if raising is not allowed).
        """
        p = self.to_act
        if p is None:
            raise IllegalAction("nobody is to act")
        owed = self.current_bet - p.bet
        call_amount = min(owed, p.stack) if owed > 0 else None

        others_can_act = any(self._can_act(q) for q in self.players if q is not p)
        reopened = (not p.acted) or (self.current_bet - p.acted_facing >= self.min_raise)
        raise_range = None
        if others_can_act and reopened and p.stack > owed:
            max_to = p.bet + p.stack
            min_to = min(self.current_bet + self.min_raise, max_to)
            raise_range = {"min": min_to, "max": max_to}

        return {
            "fold": True,
            "check": owed <= 0,
            "call": call_amount,
            "raise": raise_range,
        }

    # ------------------------------------------------------------------ actions

    def apply(self, action: Action) -> None:
        if self.done:
            raise IllegalAction("the hand is over")
        p = self.to_act
        assert p is not None
        legal = self.legal_actions()
        kind = action.kind

        if kind == "fold":
            p.folded = True
            self._record(p, "fold", None)
        elif kind == "check":
            if not legal["check"]:
                raise IllegalAction(
                    f"cannot check, there is a bet of {self.current_bet} "
                    f"(you would need to call {legal['call']})"
                )
            self._record(p, "check", None)
        elif kind == "call":
            if legal["call"] is None:
                raise IllegalAction("nothing to call, use check")
            added = self._put_in(p, legal["call"])
            self._record(p, "call", added)
        elif kind == "raise":
            rng = legal["raise"]
            if rng is None:
                raise IllegalAction("raising is not allowed right now")
            to = action.amount
            if to is None:
                raise IllegalAction("raise needs an amount (the total bet to raise to)")
            if not (rng["min"] <= to <= rng["max"]):
                raise IllegalAction(
                    f"raise amount must be between {rng['min']} and {rng['max']} (raise TO), got {to}"
                )
            increase = to - self.current_bet
            self._put_in(p, to - p.bet)
            if increase >= self.min_raise:
                self.min_raise = increase
            self.current_bet = max(self.current_bet, to)
            self._record(p, "raise", to)
        else:
            raise IllegalAction(f"unknown action {kind!r}")

        p.acted = True
        p.acted_facing = self.current_bet
        self._continue_from(self.to_act_index + 1)  # type: ignore[operator]

    def _record(self, p: PlayerState, kind: str, amount: int | None) -> None:
        self._emit(
            "action",
            **self._seat_info(p),
            street=self.street,
            action=kind,
            amount=amount,
            bet=p.bet,
            stack=p.stack,
            all_in=p.all_in,
            pot=self.pot,
        )

    # ------------------------------------------------------------------ flow

    def _continue_from(self, start: int) -> None:
        if len(self._live()) == 1:
            self._return_uncalled()
            self._award_uncontested()
            return
        for i in self._order_from(start):
            if self._needs_to_act(self._p(i)):
                self.to_act_index = i
                return
        self._end_street()

    def _end_street(self) -> None:
        self.to_act_index = None
        self._return_uncalled()
        for p in self.players:
            p.bet = 0
            p.acted = False
            p.acted_facing = 0
        self.current_bet = 0
        self.min_raise = self.big_blind

        if self.street == "river":
            self._showdown()
            return

        if sum(1 for p in self.players if self._can_act(p)) <= 1:
            # nobody (or only one player) can still bet: show cards and run the board out
            self._reveal()
            while self.street != "river":
                self._next_street()
            self._showdown()
            return

        self._next_street()
        self._continue_from(self.button_index + 1)

    def _next_street(self) -> None:
        idx = STREETS.index(self.street) + 1
        self.street = STREETS[idx]
        new = self._draw(3 if self.street == "flop" else 1)
        self.board.extend(new)
        self._emit("street", street=self.street, cards=new, board=list(self.board), pot=self.pot)

    def _return_uncalled(self) -> None:
        by_bet = sorted(self.players, key=lambda q: q.bet, reverse=True)
        top, second = by_bet[0], by_bet[1]
        diff = top.bet - second.bet
        if diff > 0:
            top.bet -= diff
            top.committed -= diff
            top.stack += diff
            top.all_in = False
            self._emit("uncalled", **self._seat_info(top), amount=diff)

    def _reveal(self) -> None:
        if self.revealed:
            return
        self.revealed = True
        self._emit(
            "showdown",
            hands=[{**self._seat_info(p), "cards": list(p.hole)} for p in self._live()],
        )

    def _award_uncontested(self) -> None:
        self.to_act_index = None
        winner = self._live()[0]
        amount = self.pot
        winner.stack += amount
        self._emit(
            "win",
            pot=0,
            amount=amount,
            winners=[{**self._seat_info(winner), "amount": amount}],
            hand=None,
        )
        self._finish()

    def _pots(self) -> list[tuple[int, list[PlayerState]]]:
        remaining = {id(p): p.committed for p in self.players}
        pots: list[tuple[int, list[PlayerState]]] = []
        while sum(remaining.values()) > 0:
            eligible = [p for p in self._live() if remaining[id(p)] > 0]
            if not eligible:  # only dead money left, add it to the last pot
                amount, elig = pots[-1]
                pots[-1] = (amount + sum(remaining.values()), elig)
                break
            level = min(remaining[id(p)] for p in eligible)
            amount = 0
            for p in self.players:
                take = min(remaining[id(p)], level)
                remaining[id(p)] -= take
                amount += take
            if pots and {id(p) for p in pots[-1][1]} == {id(p) for p in eligible}:
                pots[-1] = (pots[-1][0] + amount, eligible)
            else:
                pots.append((amount, eligible))
        return pots

    def _showdown(self) -> None:
        self.to_act_index = None
        self._reveal()
        scores = {id(p): C.evaluate(p.hole, self.board) for p in self._live()}
        position = {id(p): k for k, p in enumerate(
            self._p(i) for i in self._order_from(self.button_index + 1))}

        for pot_index, (amount, eligible) in enumerate(self._pots()):
            best = min(scores[id(p)] for p in eligible)
            winners = sorted((p for p in eligible if scores[id(p)] == best),
                             key=lambda p: position[id(p)])
            share, odd = divmod(amount, len(winners))
            paid = []
            for k, w in enumerate(winners):
                won = share + (1 if k < odd else 0)
                w.stack += won
                paid.append({**self._seat_info(w), "amount": won})
            self._emit(
                "win",
                pot=pot_index,
                amount=amount,
                winners=paid,
                hand=C.hand_name(best),
            )
        self._finish()

    def _finish(self) -> None:
        self.done = True
        self.to_act_index = None
        self._emit(
            "hand_end",
            board=list(self.board),
            results=[
                {
                    **self._seat_info(p),
                    "player_id": p.player_id,
                    "start_stack": p.start_stack,
                    "stack": p.stack,
                    "net": p.stack - p.start_stack,
                    "cards": list(p.hole),
                }
                for p in self.players
            ],
        )

    # ------------------------------------------------------------------ views

    def public_events(self) -> list[dict[str, Any]]:
        """Events without private hole cards (safe for spectators and opponents)."""
        return [e for e in self.events if e["type"] != "deal_hole"]

    def player_view(self, p: PlayerState) -> dict[str, Any]:
        return {
            "seat": p.seat,
            "name": p.name,
            "stack": p.stack,
            "bet": p.bet,
            "committed": p.committed,
            "status": p.status,
        }


def normalize_action(legal: dict[str, Any], kind: str, amount: Any = None) -> Action:
    """Turn what a bot sent into a legal Action, or raise IllegalAction with a helpful reason.

    Accepted spellings: fold, check, call, raise (amount = total bet to raise TO),
    bet (same as raise) and allin / all_in (raise as high as possible, or call if
    raising is not possible). "call" with nothing to call is treated as check.
    """
    kind = (kind or "").strip().lower().replace("-", "_")
    if kind == "bet":
        kind = "raise"
    if kind in ("allin", "all_in"):
        if legal["raise"]:
            return Action("raise", legal["raise"]["max"])
        kind = "call" if legal["call"] is not None else "check"
    if kind == "fold":
        return Action("fold")
    if kind == "check":
        if not legal["check"]:
            raise IllegalAction(f"cannot check: you have to call {legal['call']}, raise or fold")
        return Action("check")
    if kind == "call":
        if legal["call"] is None:
            return Action("check")
        return Action("call")
    if kind == "raise":
        rng = legal["raise"]
        if rng is None:
            raise IllegalAction("raising is not allowed right now (see legal.raise = null); call, check or fold")
        if amount is None:
            raise IllegalAction("raise needs an 'amount': the total bet you want to raise TO")
        if isinstance(amount, bool):
            raise IllegalAction("amount must be a whole number")
        if isinstance(amount, float) and amount.is_integer():
            amount = int(amount)
        if isinstance(amount, str) and amount.strip().isdigit():
            amount = int(amount.strip())
        if not isinstance(amount, int):
            raise IllegalAction("amount must be a whole number of chips")
        if not rng["min"] <= amount <= rng["max"]:
            raise IllegalAction(
                f"raise amount {amount} is out of range: raise TO between {rng['min']} and {rng['max']}"
            )
        return Action("raise", amount)
    raise IllegalAction(f"unknown action {kind!r}; use fold, check, call or raise")
