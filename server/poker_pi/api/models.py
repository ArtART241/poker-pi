"""Request/response models. They exist mostly to produce a precise OpenAPI spec."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Error(BaseModel):
    detail: str = Field(description="Human readable explanation of what went wrong.")


class RaiseRange(BaseModel):
    min: int = Field(description="Smallest total bet you may raise TO.")
    max: int = Field(description="Largest total bet you may raise TO (= all-in).")


class Legal(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    fold: bool = Field(description="Folding is always allowed.")
    check: bool = Field(description="True if nothing is owed, so you may check.")
    call: int | None = Field(description="Chips that calling ADDS to your bet, or null if there is nothing to call.")
    raise_: RaiseRange | None = Field(
        alias="raise", description="Allowed range for a raise (raise TO), or null if raising is not allowed."
    )


class PlayerView(BaseModel):
    seat: int
    name: str
    stack: int = Field(description="Chips behind (not counting chips already bet).")
    bet: int = Field(description="Chips this player has bet on the current street.")
    committed: int = Field(description="Chips this player has put into the pot during the whole hand.")
    status: Literal["active", "folded", "all_in"]
    is_you: bool


class BlindsInfo(BaseModel):
    small: int
    big: int
    ante: int
    level: int
    hands_until_next_level: int


class TurnState(BaseModel):
    turn_id: str = Field(description="Send this back with your action.")
    deadline_ms: int = Field(description="Milliseconds left to answer before you are auto-checked/folded.")
    table_id: str
    tournament_id: int | None
    practice: bool
    hand_id: int
    hand_no: int = Field(description="Number of the hand at this table (1, 2, 3, ...).")
    seat: int = Field(description="Your seat (0-8).")
    name: str
    hole_cards: list[str] = Field(description='Your two private cards, e.g. ["Ah", "Td"].')
    stack: int = Field(description="Your chips behind.")
    bet: int = Field(description="What you already bet on this street.")
    street: Literal["preflop", "flop", "turn", "river"]
    board: list[str] = Field(description="Community cards (0, 3, 4 or 5).")
    pot: int = Field(description="All chips in the middle, including the bets of this street.")
    current_bet: int = Field(description="Highest bet on this street.")
    to_call: int = Field(description="Chips needed to call (0 if you can check).")
    legal: Legal
    blinds: BlindsInfo
    button: int = Field(description="Seat of the dealer button.")
    players: list[PlayerView]
    action_log: list[dict[str, Any]] = Field(description="Everything public that happened in this hand so far.")


class ActionRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [
        {"turn_id": "t_3f9a0c1b2d4e5f60", "action": "call"},
        {"turn_id": "t_3f9a0c1b2d4e5f60", "action": "raise", "amount": 120},
    ]})

    turn_id: str = Field(description="The turn_id you received from GET /turn.")
    action: str = Field(description="fold | check | call | raise (also accepted: bet = raise, allin).")
    amount: int | None = Field(default=None, description="Only for raise: the total bet to raise TO.")


class ActionResponse(BaseModel):
    accepted: bool
    action: str
    amount: int | None = None


class TableRef(BaseModel):
    table_id: str
    kind: Literal["tournament", "practice"]
    seat: int
    stack: int
    status: str


class MeResponse(BaseModel):
    id: str
    name: str
    owner: str
    tables: list[TableRef] = Field(description="Tables you are currently seated at.")
    open_turns: int = Field(description="Turns waiting for your answer right now.")
    registered_tournaments: list[int]
    stats: dict[str, Any]


class TournamentInfo(BaseModel):
    id: int
    name: str
    status: Literal["registering", "running", "finished", "cancelled"]
    start_at: str
    started_at: str | None
    finished_at: str | None
    note: str | None
    table_id: str
    players: list[str] = Field(description="Registered bots (or the field, once started).")
    max_players: int
    starting_stack: int
    hands_per_level: int
    registered: bool | None = Field(default=None, description="Whether YOUR bot is registered (bot API only).")
    winner: str | None = None


class RegistrationResponse(BaseModel):
    tournament_id: int
    registered: bool


class PracticeRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [
        {"opponents": ["random", "station", "tight"], "speed": "fast"},
    ]})

    opponents: list[Literal["random", "station", "tight"]] = Field(
        default_factory=lambda: ["random", "station", "tight"], min_length=1, max_length=8,
        description="House bots to play against: random, station (calls everything), tight (only plays good hands).",
    )
    speed: Literal["fast", "live"] = Field(
        default="fast", description="fast: no pauses. live: same pace as tournaments, nice to watch in the browser.")
    starting_stack: int = Field(default=1500, ge=100, le=100_000)


class PracticeResponse(BaseModel):
    table_id: str
    status: str
    finish_reason: str | None
    hand_no: int
    players: list[dict[str, Any]]
    watch_url: str


class HandSummary(BaseModel):
    id: int
    table_id: str
    tournament_id: int | None
    practice: bool
    hand_no: int
    started_at: str
    ended_at: str | None
    blinds: list[int] | None
    players: list[str]
    pot: int
    winners: list[str]
    winning_hand: str | None
    board: list[str]
    showdown: bool


class HandDetail(BaseModel):
    id: int
    table_id: str
    tournament_id: int | None
    practice: bool
    hand_no: int
    started_at: str
    ended_at: str | None
    events: list[dict[str, Any]] = Field(description="Complete history including everybody's hole cards.")
